"""
Oracle Free Tier - PARALLEL Auto Retry VM Launch Script (VERBOSE)
==================================================================
Sends multiple parallel requests with FULL visibility into what's happening.

Usage: python parallel_retry_launch.py
To stop: Press Ctrl+C
"""

import subprocess
import os
import time
import datetime
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ============ CONFIGURATION ============
HOME = os.path.expanduser("~")
OCI_PATH = os.path.join(HOME, "bin", "oci.exe")
SSH_KEY_PATH = os.path.join(HOME, ".ssh", "oracle_free_tier.pub")

COMPARTMENT_ID = "ocid1.tenancy.oc1..aaaaaaaao2epz5zw6eiv4vijdjj7n7whds5khyffbqblymobiypi5ozppglq"
AVAILABILITY_DOMAIN = "fjqo:EU-PARIS-1-AD-1"
SUBNET_ID = "ocid1.subnet.oc1.eu-paris-1.aaaaaaaaifzidw6bnh3d4mwf5xqyiwsckbxalgmqtxjaqdx6yo3ncsd4aouq"
IMAGE_ID = "ocid1.image.oc1.eu-paris-1.aaaaaaaaqb3hjmnty4rvidngmb2m4pqtmnrqingxqxqhutffjogbxw6hzcga"

SHAPE = "VM.Standard.A1.Flex"
OCPUS = 2
MEMORY_GB = 12
BOOT_VOLUME_GB = 100
DISPLAY_NAME = "free-tier-ubuntu"
ENDPOINT = "https://iaas.eu-paris-1.oraclecloud.com/20160918/instances"

PARALLEL_REQUESTS = 3       # عدد الطلبات المتوازية في كل محاولة
RETRY_INTERVAL_SECONDS = 25 # نحاول كل 25 ثانية
MAX_ROUNDS = 2880           # 2880 × 30s = 24 ساعة
REQUEST_TIMEOUT = 60        # timeout أقصر = محاولات أسرع
# =======================================

os.environ["SUPPRESS_LABEL_WARNING"] = "True"

# Thread-safe printing
print_lock = threading.Lock()
success_event = threading.Event()
success_lock = threading.Lock()
success_result = {"data": None}


def log(msg, thread_id=None):
    """Thread-safe timestamped print."""
    now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    prefix = f"  [T{thread_id+1}]" if thread_id is not None else "  "
    with print_lock:
        print(f"  {now} {prefix} {msg}", flush=True)


def launch_instance(thread_id):
    """Attempt to launch the instance with verbose output."""
    if success_event.is_set():
        return False, "Skipped", thread_id

    log(f"📤 POST → {ENDPOINT}", thread_id)
    log(f"   Shape: {SHAPE} | {OCPUS} OCPU | {MEMORY_GB}GB RAM | {BOOT_VOLUME_GB}GB Disk", thread_id)
    log(f"   Image: Ubuntu 24.04 ARM | AD: {AVAILABILITY_DOMAIN.split(':')[-1]}", thread_id)
    log(f"   ⏳ Waiting for Oracle response (timeout: {REQUEST_TIMEOUT}s)...", thread_id)

    cmd = [
        OCI_PATH, "compute", "instance", "launch",
        "--compartment-id", COMPARTMENT_ID,
        "--availability-domain", AVAILABILITY_DOMAIN,
        "--shape", SHAPE,
        "--shape-config", json.dumps({"ocpus": OCPUS, "memoryInGBs": MEMORY_GB}),
        "--image-id", IMAGE_ID,
        "--subnet-id", SUBNET_ID,
        "--assign-public-ip", "true",
        "--display-name", DISPLAY_NAME,
        "--boot-volume-size-in-gbs", str(BOOT_VOLUME_GB),
        "--ssh-authorized-keys-file", SSH_KEY_PATH,
        "--output", "json",
        "--read-timeout", str(REQUEST_TIMEOUT),
        "--connection-timeout", str(REQUEST_TIMEOUT),
    ]

    start_time = time.time()

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=REQUEST_TIMEOUT + 30)
        elapsed = time.time() - start_time

        if result.returncode == 0:
            log(f"✅ HTTP 200 OK ({elapsed:.1f}s) — INSTANCE CREATED!", thread_id)
            with success_lock:
                success_event.set()
                success_result["data"] = result.stdout
            return True, result.stdout, thread_id
        else:
            # Parse the error
            stderr = result.stderr or ""
            try:
                # Find JSON in stderr
                json_start = stderr.find('{')
                json_end = stderr.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    err_data = json.loads(stderr[json_start:json_end])
                    code = err_data.get("code", "Unknown")
                    message = err_data.get("message", "No message")
                    status = err_data.get("status", "?")
                    opc_id = err_data.get("opc-request-id", "")
                    if opc_id:
                        opc_short = opc_id.split('/')[0][:12] + "..."
                    else:
                        opc_short = "N/A"

                    if "Out of host capacity" in message:
                        log(f"❌ HTTP {status} ({elapsed:.1f}s) — {code}: {message}", thread_id)
                        log(f"   Request ID: {opc_short}", thread_id)
                    elif "LimitExceeded" in code:
                        log(f"⚠️  HTTP {status} ({elapsed:.1f}s) — LIMIT EXCEEDED!", thread_id)
                        log(f"   {message}", thread_id)
                    else:
                        log(f"❌ HTTP {status} ({elapsed:.1f}s) — {code}: {message}", thread_id)
                else:
                    log(f"❌ Failed ({elapsed:.1f}s) — {stderr[:120]}", thread_id)
            except json.JSONDecodeError:
                log(f"❌ Failed ({elapsed:.1f}s) — {stderr[:120]}", thread_id)

            return False, stderr, thread_id

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        log(f"⏱️  TIMEOUT ({elapsed:.1f}s) — Server didn't respond in time", thread_id)
        return False, "Connection timed out", thread_id
    except Exception as e:
        elapsed = time.time() - start_time
        log(f"💥 ERROR ({elapsed:.1f}s) — {str(e)[:100]}", thread_id)
        return False, str(e), thread_id


def run_parallel_round(round_num):
    """Run multiple parallel launch attempts."""
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"\n{'─'*60}")
    print(f"  🔄 Round {round_num}/{MAX_ROUNDS} | {now} | {PARALLEL_REQUESTS} parallel requests")
    print(f"{'─'*60}")

    # Reset success event for new round
    success_event.clear()

    with ThreadPoolExecutor(max_workers=PARALLEL_REQUESTS) as executor:
        futures = {
            executor.submit(launch_instance, i): i
            for i in range(PARALLEL_REQUESTS)
        }

        for future in as_completed(futures):
            success, message, thread_id = future.result()

            if success and "LimitExceeded" not in str(message):
                return True, message

            if "LimitExceeded" in str(message) or "limit" in str(message).lower():
                return True, message

    return False, "All threads failed"


def main():
    print()
    print("  ⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡")
    print("  ⚡  Oracle Free Tier - PARALLEL Auto Retry (VERBOSE)  ⚡")
    print("  ⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡")
    print()
    print(f"  🖥️  Shape:         {SHAPE} (ARM Ampere)")
    print(f"  🔧 OCPUs:         {OCPUS}")
    print(f"  💾 Memory:        {MEMORY_GB} GB")
    print(f"  💿 Boot Volume:   {BOOT_VOLUME_GB} GB")
    print(f"  🐧 OS:            Ubuntu 24.04 aarch64")
    print(f"  🌍 Region:        eu-paris-1 (France Central, Paris)")
    print(f"  🔗 Endpoint:      {ENDPOINT}")
    print(f"  🔀 Threads:       {PARALLEL_REQUESTS} per round")
    print(f"  ⏱️  Interval:      {RETRY_INTERVAL_SECONDS}s between rounds")
    print(f"  📊 Max Rounds:    {MAX_ROUNDS} (~{MAX_ROUNDS * RETRY_INTERVAL_SECONDS // 3600}h)")
    print()
    print(f"  Press Ctrl+C to stop at any time.")

    total_requests = 0
    start_time = time.time()

    for round_num in range(1, MAX_ROUNDS + 1):
        success, message = run_parallel_round(round_num)
        total_requests += PARALLEL_REQUESTS

        elapsed_total = time.time() - start_time
        mins = int(elapsed_total // 60)
        secs = int(elapsed_total % 60)

        if success:
            if "LimitExceeded" in str(message) or "limit" in str(message).lower():
                print(f"\n  ⚠️  Limit reached! Check Oracle Console for existing VMs.")
                return

            print()
            print(f"  {'🎉'*20}")
            print(f"  🎉  VM CREATED SUCCESSFULLY!  🎉")
            print(f"  {'🎉'*20}")
            print()

            try:
                import winsound
                for _ in range(3):
                    winsound.Beep(1200, 500)
                    winsound.Beep(1600, 500)
            except Exception:
                pass

            try:
                data = json.loads(message)
                instance = data.get("data", {})
                shape_config = instance.get("shape-config", {})
                print(f"  Instance ID:    {instance.get('id', 'N/A')}")
                print(f"  Display Name:   {instance.get('display-name', 'N/A')}")
                print(f"  State:          {instance.get('lifecycle-state', 'N/A')}")
                print(f"  Shape:          {instance.get('shape', 'N/A')}")
                if shape_config:
                    print(f"  OCPUs:          {shape_config.get('ocpus', 'N/A')}")
                    print(f"  Memory:         {shape_config.get('memory-in-gbs', 'N/A')} GB")
                print(f"  Time Created:   {instance.get('time-created', 'N/A')}")
            except (json.JSONDecodeError, TypeError):
                print(message)

            print(f"\n  📊 Stats: {total_requests} requests in {mins}m {secs}s")
            print()
            print(f"  📋 Next steps:")
            print(f"  1. Wait 2-3 minutes for the VM to boot")
            print(f"  2. Check Oracle Console → Compute → Instances for Public IP")
            print(f'  3. SSH: ssh -i "{os.path.join(HOME, ".ssh", "oracle_free_tier")}" ubuntu@<PUBLIC_IP>')

            details_path = os.path.join("d:\\oracle free tier", "instance_details.json")
            with open(details_path, "w") as f:
                f.write(message)
            print(f"\n  💾 Details saved to: {details_path}")
            return

        # Round summary
        print(f"\n  📊 Round {round_num} done | Total: {total_requests} requests | Running: {mins}m {secs}s")
        print(f"  ⏳ Next round in {RETRY_INTERVAL_SECONDS}s...", flush=True)

        try:
            time.sleep(RETRY_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print(f"\n\n  ⏹️  Stopped. Sent {total_requests} requests in {mins}m {secs}s")
            return

    print(f"\n  Max rounds reached. Total: {total_requests} requests")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  ⏹️  Stopped by user.")
