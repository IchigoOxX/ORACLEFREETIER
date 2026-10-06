"""
Oracle Free Tier - Auto Retry VM Launch Script
===============================================
This script keeps retrying to create an ARM A1 instance until capacity is available.

Usage: python auto_retry_launch.py
To stop: Press Ctrl+C

Specs: 4 OCPU | 24 GB RAM | 200 GB Boot Volume | Ubuntu 24.04 ARM
"""

import subprocess
import os
import time
import datetime
import json
import sys

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

RETRY_INTERVAL_SECONDS = 45  # Retry every 45 seconds
MAX_RETRIES = 1440  # Max 24 hours of retrying (1440 * 60s = 24h)
# =======================================

os.environ["SUPPRESS_LABEL_WARNING"] = "True"
os.environ["OCI_CLI_READ_TIMEOUT"] = "300"


def launch_instance():
    """Attempt to launch the instance. Returns (success, message)."""
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
        "--output", "json"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Connection timed out"
    except Exception as e:
        return False, str(e)


def main():
    print("=" * 60)
    print("  Oracle Free Tier - Auto Retry VM Launch")
    print("=" * 60)
    print(f"  Shape:       {SHAPE}")
    print(f"  OCPUs:       {OCPUS}")
    print(f"  Memory:      {MEMORY_GB} GB")
    print(f"  Boot Volume: {BOOT_VOLUME_GB} GB")
    print(f"  Image:       Ubuntu 24.04 ARM (aarch64)")
    print(f"  Region:      eu-paris-1 (France Central)")
    print(f"  Retry Every: {RETRY_INTERVAL_SECONDS} seconds")
    print(f"  Max Retries: {MAX_RETRIES}")
    print("=" * 60)
    print()
    print("Press Ctrl+C to stop at any time.")
    print()

    for attempt in range(1, MAX_RETRIES + 1):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] Attempt {attempt}/{MAX_RETRIES} — Sending launch request...", flush=True)

        success, message = launch_instance()

        if success:
            print("  🎉 SUCCESS! VM CREATED SUCCESSFULLY! 🎉")
            print()
            print("=" * 60)
            print("  VM CREATED SUCCESSFULLY!")
            print("=" * 60)

            try:
                import winsound
                for _ in range(5):
                    winsound.Beep(1200, 400)
                    winsound.Beep(1600, 400)
            except Exception:
                pass

            # Parse and display instance details
            try:
                data = json.loads(message)
                instance = data.get("data", {})
                print(f"  Instance ID: {instance.get('id', 'N/A')}")
                print(f"  Display Name: {instance.get('display-name', 'N/A')}")
                print(f"  State: {instance.get('lifecycle-state', 'N/A')}")
                print(f"  Shape: {instance.get('shape', 'N/A')}")
            except json.JSONDecodeError:
                print(message)

            print()
            print("Next steps:")
            print("  1. Wait a few minutes for the VM to fully boot")
            print("  2. Get the public IP from Oracle Console or run:")
            print(f'     {OCI_PATH} compute instance list-vnics --instance-id <INSTANCE_ID>')
            print(f"  3. SSH into the VM:")
            print(f'     ssh -i "{os.path.join(HOME, ".ssh", "oracle_free_tier")}" ubuntu@<PUBLIC_IP>')
            print()

            # Save instance details
            with open(os.path.join("d:\\oracle free tier", "instance_details.json"), "w") as f:
                f.write(message)
            print("Instance details saved to: d:\\oracle free tier\\instance_details.json")
            return

        # Handle specific Oracle Cloud error codes
        sleep_time = RETRY_INTERVAL_SECONDS
        if "Out of host capacity" in message:
            print(f"❌ Out of capacity in Paris. Retrying in {sleep_time}s...")
        elif "TooManyRequests" in message:
            sleep_time = 60
            print(f"⏳ Rate limited by Oracle (TooManyRequests). Cooling down for {sleep_time}s...")
        elif "timed out" in message.lower():
            print(f"⏱️ Timed out. Retrying in {sleep_time}s...")
        elif "LimitExceeded" in message:
            sleep_time = 45
            print(f"⚠️ Limit collision or VM in-flight. Retrying in {sleep_time}s...")
        else:
            # Shorten message
            clean_msg = message.replace('\n', ' ')[:100]
            print(f"❌ Error: {clean_msg}...")
            print(f"   Retrying in {sleep_time}s...")

        try:
            time.sleep(sleep_time)
        except KeyboardInterrupt:
            print("\n\nStopped by user. You can run this script again later.")
            return

    print(f"\nMax retries ({MAX_RETRIES}) reached. Try again later or try a different region.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStopped by user. You can run this script again later.")
    except Exception as e:
        import traceback
        print(f"\nCRITICAL ERROR: {e}")
        traceback.print_exc()
        try:
            with open(os.path.join("d:\\oracle free tier", "crash.log"), "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
        except Exception:
            pass
