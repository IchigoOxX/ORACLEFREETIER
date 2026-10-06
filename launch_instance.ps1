$env:Path = "$HOME\bin;$HOME\lib\oracle-cli\Scripts;" + $env:Path
$env:SUPPRESS_LABEL_WARNING = "True"

# Write shape config to temp file
$shapeConfigFile = "$env:TEMP\shape_config.json"
@'
{"ocpus":2,"memoryInGBs":12}
'@ | Out-File -FilePath $shapeConfigFile -Encoding ascii -NoNewline

oci compute instance launch `
  --compartment-id "ocid1.tenancy.oc1..aaaaaaaao2epz5zw6eiv4vijdjj7n7whds5khyffbqblymobiypi5ozppglq" `
  --availability-domain "fjqo:EU-PARIS-1-AD-1" `
  --shape "VM.Standard.A1.Flex" `
  --shape-config "file://$shapeConfigFile" `
  --image-id "ocid1.image.oc1.eu-paris-1.aaaaaaaaqb3hjmnty4rvidngmb2m4pqtmnrqingxqxqhutffjogbxw6hzcga" `
  --subnet-id "ocid1.subnet.oc1.eu-paris-1.aaaaaaaaifzidw6bnh3d4mwf5xqyiwsckbxalgmqtxjaqdx6yo3ncsd4aouq" `
  --assign-public-ip true `
  --display-name "free-tier-ubuntu" `
  --boot-volume-size-in-gbs 100 `
  --ssh-authorized-keys-file "$HOME\.ssh\oracle_free_tier.pub" `
  --output json
