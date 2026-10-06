import subprocess, os

home = os.path.expanduser("~")
oci_path = os.path.join(home, "bin", "oci.exe")
ssh_key = os.path.join(home, ".ssh", "oracle_free_tier.pub")

os.environ["SUPPRESS_LABEL_WARNING"] = "True"
os.environ["OCI_CLI_READ_TIMEOUT"] = "300"

cmd = [
    oci_path, "compute", "instance", "launch",
    "--compartment-id", "ocid1.tenancy.oc1..aaaaaaaao2epz5zw6eiv4vijdjj7n7whds5khyffbqblymobiypi5ozppglq",
    "--availability-domain", "fjqo:EU-PARIS-1-AD-1",
    "--shape", "VM.Standard.A1.Flex",
    "--shape-config", '{"ocpus":2,"memoryInGBs":12}',
    "--image-id", "ocid1.image.oc1.eu-paris-1.aaaaaaaaqb3hjmnty4rvidngmb2m4pqtmnrqingxqxqhutffjogbxw6hzcga",
    "--subnet-id", "ocid1.subnet.oc1.eu-paris-1.aaaaaaaaifzidw6bnh3d4mwf5xqyiwsckbxalgmqtxjaqdx6yo3ncsd4aouq",
    "--assign-public-ip", "true",
    "--display-name", "free-tier-ubuntu",
    "--boot-volume-size-in-gbs", "100",
    "--ssh-authorized-keys-file", ssh_key,
    "--output", "json"
]

print("Launching instance...")
result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
print("STDOUT:", result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
print("Return code:", result.returncode)
