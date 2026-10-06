"""
Oracle Cloud Free Tier - GitHub Actions Auto-Retry Bot
======================================================
Runs in GitHub Actions cloud 24/7 to catch Oracle ARM A1 capacity.
Features:
- Rotates through Fault Domains (FAULT-DOMAIN-1, FAULT-DOMAIN-2, FAULT-DOMAIN-3).
- WhatsApp notifications (via CallMeBot API).
- Telegram notifications (optional).
- Smart backoff for rate limiting (429).
"""

import os
import sys
import time
import datetime
import urllib.parse
import urllib.request
import oci

# Environment variables provided by GitHub Actions Secrets
OCI_USER = os.getenv("OCI_USER")
OCI_TENANCY = os.getenv("OCI_TENANCY")
OCI_FINGERPRINT = os.getenv("OCI_FINGERPRINT")
OCI_REGION = os.getenv("OCI_REGION", "eu-paris-1")
OCI_KEY_CONTENT = os.getenv("OCI_KEY_CONTENT")

COMPARTMENT_ID = os.getenv("OCI_COMPARTMENT_ID", OCI_TENANCY)
AVAILABILITY_DOMAIN = os.getenv("OCI_AVAILABILITY_DOMAIN", "fjqo:EU-PARIS-1-AD-1")
SUBNET_ID = os.getenv("OCI_SUBNET_ID", "ocid1.subnet.oc1.eu-paris-1.aaaaaaaaifzidw6bnh3d4mwf5xqyiwsckbxalgmqtxjaqdx6yo3ncsd4aouq")
IMAGE_ID = os.getenv("OCI_IMAGE_ID", "ocid1.image.oc1.eu-paris-1.aaaaaaaaqb3hjmnty4rvidngmb2m4pqtmnrqingxqxqhutffjogbxw6hzcga")
SSH_AUTHORIZED_KEYS = os.getenv("SSH_AUTHORIZED_KEYS")

# WhatsApp & Telegram Notifications (Optional)
WHATSAPP_PHONE = os.getenv("WHATSAPP_PHONE")      # e.g., +2010xxxxxxxx
WHATSAPP_APIKEY = os.getenv("WHATSAPP_APIKEY")    # From CallMeBot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# VM Specs
SHAPE = "VM.Standard.A1.Flex"
OCPUS = int(os.getenv("VM_OCPUS", "2"))
MEMORY_GB = int(os.getenv("VM_MEMORY_GB", "12"))
BOOT_VOLUME_GB = int(os.getenv("BOOT_VOLUME_GB", "100"))
DISPLAY_NAME = "oracle-arm-free-tier"

FAULT_DOMAINS = ["FAULT-DOMAIN-1", "FAULT-DOMAIN-2", "FAULT-DOMAIN-3"]

# Interval settings: fast checks without getting rate limited
RETRY_INTERVAL = int(os.getenv("RETRY_INTERVAL", "30"))
MAX_MINUTES = int(os.getenv("MAX_MINUTES", "300")) # GitHub Action run limit ~5-6h max


def send_notification(text):
    """Send success alert via WhatsApp and/or Telegram."""
    # 1. WhatsApp via CallMeBot
    if WHATSAPP_PHONE and WHATSAPP_APIKEY:
        try:
            encoded_text = urllib.parse.quote(text)
            url = f"https://api.callmebot.com/whatsapp.php?phone={WHATSAPP_PHONE}&text={encoded_text}&apikey={WHATSAPP_APIKEY}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            urllib.request.urlopen(req, timeout=15)
            print("  📱 WhatsApp notification sent successfully!")
        except Exception as e:
            print(f"  ⚠️ Failed to send WhatsApp message: {e}")

    # 2. Telegram
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            encoded_text = urllib.parse.quote(text)
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={encoded_text}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            urllib.request.urlopen(req, timeout=15)
            print("  📱 Telegram notification sent successfully!")
        except Exception as e:
            print(f"  ⚠️ Failed to send Telegram message: {e}")


def get_oci_client():
    """Initialize OCI Compute Client directly in memory."""
    config = {
        "user": OCI_USER,
        "key_content": OCI_KEY_CONTENT,
        "fingerprint": OCI_FINGERPRINT,
        "tenancy": OCI_TENANCY,
        "region": OCI_REGION
    }
    oci.config.validate_config(config)
    return oci.compute.ComputeClient(config)


def main():
    print("=" * 60)
    print("  Oracle Cloud Always Free - ARM Capacity Hunter")
    print("=" * 60)
    print(f"  Shape:        {SHAPE}")
    print(f"  OCPUs:        {OCPUS}")
    print(f"  RAM:          {MEMORY_GB} GB")
    print(f"  Boot Volume:  {BOOT_VOLUME_GB} GB")
    print(f"  Region:       {OCI_REGION}")
    print(f"  AD:           {AVAILABILITY_DOMAIN}")
    print(f"  Fault Domains: Rotating across {FAULT_DOMAINS}")
    print(f"  Interval:     {RETRY_INTERVAL}s")
    print("=" * 60)
    print()

    client = get_oci_client()

    start_time = time.time()
    attempt = 0
    fd_index = 0

    while True:
        elapsed_min = (time.time() - start_time) / 60
        if elapsed_min >= MAX_MINUTES:
            print(f"\nReached max execution time of {MAX_MINUTES} minutes. Ending this workflow run.")
            sys.exit(0)

        attempt += 1
        current_fd = FAULT_DOMAINS[fd_index % len(FAULT_DOMAINS)]
        fd_index += 1

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] Attempt {attempt} ({current_fd})...", end=" ", flush=True)

        launch_details = oci.compute.models.LaunchInstanceDetails(
            compartment_id=COMPARTMENT_ID,
            availability_domain=AVAILABILITY_DOMAIN,
            fault_domain=current_fd,
            shape=SHAPE,
            shape_config=oci.compute.models.LaunchInstanceShapeConfigDetails(
                ocpus=OCPUS,
                memory_in_gbs=MEMORY_GB
            ),
            display_name=DISPLAY_NAME,
            image_id=IMAGE_ID,
            source_details=oci.compute.models.InstanceSourceViaImageDetails(
                image_id=IMAGE_ID,
                boot_volume_size_in_gbs=BOOT_VOLUME_GB
            ),
            create_vnic_details=oci.compute.models.CreateVnicDetails(
                subnet_id=SUBNET_ID,
                assign_public_ip=True
            ),
            metadata={
                "ssh_authorized_keys": SSH_AUTHORIZED_KEYS or ""
            }
        )

        try:
            response = client.launch_instance(launch_details)
            instance = response.data

            print("\n🎉 SUCCESS! VM CREATED SUCCESSFULLY! 🎉")
            print(f"  Instance ID:   {instance.id}")
            print(f"  Display Name:  {instance.display_name}")
            print(f"  State:         {instance.lifecycle_state}")
            print(f"  Fault Domain:  {instance.fault_domain}")

            msg = (
                f"🎉 مبروك! تم إنشاء سيرفر أوراكل بنجاح!\n"
                f"المواصفات: {OCPUS} كور | {MEMORY_GB} جيجا رام | {BOOT_VOLUME_GB} جيجا هارد\n"
                f"الريجين: {OCI_REGION}\n"
                f"الـ ID: {instance.id[:20]}..."
            )
            send_notification(msg)
            sys.exit(0)

        except oci.exceptions.ServiceError as e:
            if "Out of host capacity" in e.message:
                print(f"❌ Out of capacity. Waiting {RETRY_INTERVAL}s...")
                time.sleep(RETRY_INTERVAL)
            elif e.status == 429 or "TooManyRequests" in e.code:
                cooldown = 70
                print(f"⏳ Rate limited (429). Cooldown for {cooldown}s...")
                time.sleep(cooldown)
            elif "LimitExceeded" in e.code:
                print(f"⚠️ Limit Exceeded: {e.message[:100]}")
                time.sleep(RETRY_INTERVAL)
            else:
                print(f"❌ Error ({e.status}): {e.message[:100]}")
                time.sleep(RETRY_INTERVAL)

        except Exception as ex:
            print(f"💥 Exception: {str(ex)[:100]}")
            time.sleep(RETRY_INTERVAL)


if __name__ == "__main__":
    main()
