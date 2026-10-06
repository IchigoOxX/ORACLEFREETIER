# Oracle Free Tier - Ubuntu ARM VM

## الحالة الحالية ✅

| Item | Status | Details |
|------|--------|---------|
| OCI CLI | ✅ Installed | v3.90.0 |
| API Key | ✅ Configured | Fingerprint: `2a:44:06:47:8a:a1:d9:4e:08:2b:8c:3e:fd:b8:ae:60` |
| SSH Key | ✅ Generated | `~/.ssh/oracle_free_tier` |
| VCN | ✅ Created | `free-tier-vcn` (10.0.0.0/16) |
| Internet Gateway | ✅ Created | `free-tier-igw` |
| Route Table | ✅ Updated | 0.0.0.0/0 → IGW |
| Security List | ✅ Updated | SSH(22), HTTP(80), HTTPS(443) |
| Public Subnet | ✅ Created | `free-tier-public-subnet` (10.0.0.0/24) |
| **VM Instance** | ⏳ Pending | "Out of host capacity" - need to retry |

## المواصفات (الحد الأقصى المتاح لحسابك)

- **Shape**: VM.Standard.A1.Flex (ARM Ampere)
- **OCPUs**: 2 (الحد الأقصى المسموح به لحسابك من أوراكل)
- **RAM**: 12 GB
- **Boot Volume**: 100 GB (متبقي 153 GB بسبب وجود Boot Volume قديم مساحته 47 GB)
- **OS**: Ubuntu 24.04 aarch64
- **Region**: eu-paris-1 (France Central, Paris)

## كيف تعمل الـ VM

### الطريقة 1: Auto-Retry Script (مُوصى بيها)

```powershell
python "d:\oracle free tier\auto_retry_launch.py"
```

السكريبت هيفضل يحاول كل 60 ثانية لحد ما يلاقي capacity. سيبه شغال في الخلفية.
اضغط `Ctrl+C` عشان توقفه.

### الطريقة 2: من Oracle Console

1. ادخل [Oracle Cloud Console](https://cloud.oracle.com)
2. اضغط **Create a VM instance**
3. اختار:
   - Image: **Canonical Ubuntu 24.04**
   - Shape: **VM.Standard.A1.Flex** → 4 OCPU, 24 GB RAM
   - Networking: اختار **free-tier-vcn** و **free-tier-public-subnet**
   - Boot Volume: غير الحجم لـ **200 GB**
   - SSH Key: ارفع الملف `C:\Users\soon3\.ssh\oracle_free_tier.pub`

## بعد ما الـ VM تتعمل

### اتصل بالـ SSH

```powershell
ssh -i "$HOME\.ssh\oracle_free_tier" ubuntu@<PUBLIC_IP>
```

### تحديث النظام

```bash
sudo apt update && sudo apt upgrade -y
```

### تأكد من المواصفات

```bash
# Check CPUs
nproc

# Check RAM
free -h

# Check Disk
df -h
```

## ملفات مهمة

| File | Description |
|------|-------------|
| `~\.oci\config` | OCI CLI configuration |
| `~\.oci\oci_api_key.pem` | API private key |
| `~\.oci\oci_api_key_public.pem` | API public key |
| `~\.ssh\oracle_free_tier` | SSH private key |
| `~\.ssh\oracle_free_tier.pub` | SSH public key |
| `auto_retry_launch.py` | Auto-retry VM launch script |

## ملاحظات مهمة ⚠️

1. **"Out of host capacity"** - مشكلة شائعة جداً مع Always Free ARM instances
2. الحل: استمر في المحاولة (Auto-Retry Script) - عادة بيمشي خلال ساعات
3. **أفضل وقت للمحاولة**: الفجر أو بعد منتصف الليل (وقت أقل طلب)
4. **متعملش أكتر من VM واحدة** عشان متكسرش الـ Free Tier quota
