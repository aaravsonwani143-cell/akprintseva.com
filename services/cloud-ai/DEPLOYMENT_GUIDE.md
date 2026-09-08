# 🚀 Free Cloud AI Microservice Deployment Guide (AK Print Seva)

Yeh guide aapko batayegi ki kaise aap **100% Free** (bina kisi credit card ya extra kharche ke) apne Document AI & PDF processing engine ko cloud par live kar sakte hain. Isse aapka **Hostinger Single Web Hosting** plan bina kisi load ya crash ke smoothly chalega.

---

## 🌟 Aapko Kya Milega?
1. **₹0 Extra Kharcha**: Hostinger ka 1 CPU / 1 GB RAM plan hi use hoga.
2. **Dedicated Cloud Python Container**: OpenCV, NumPy, Pillow, aur pypdf bina kisi restriction ke chalenge.
3. **Dual Auto-Switch**:
   - Jab aap apne laptop/computer (XAMPP) par kaam karenge, toh offline local Python se chalega.
   - Jab website Hostinger par chalegi, toh cloud API se seamlessly process hoga.

---

## 🛠️ Step-by-Step Deployment (Render.com par 3 Minute me)

### Step 1: Render.com par Free Account Banayein
1. Browser me [https://render.com](https://render.com) kholein.
2. **"Get Started for Free"** par click karein (GitHub ya Email se login karein).
3. Email verify karein.

---

### Step 2: Naya Web Service Banayein
1. Render Dashboard par **"New +"** button par click karein aur **"Web Service"** chunein.
2. **Option A (GitHub se connect)**:
   - Agar aapka project GitHub repo par hai, toh repository connect karein.
3. **Option B (Public Git URL)**:
   - Repository URL select karein.

---

### Step 3: Service Settings Bharo
Form me ye details dalein:
- **Name**: `akprintseva-ai` (ya koi bhi pasandeeda naam)
- **Region**: `Singapore` (India ke sabse paas aur fast)
- **Branch**: `main`
- **Root Directory**: Chhod dein (empty)
- **Runtime**: `Python 3`
- **Build Command**:
  ```bash
  pip install -r services/cloud-ai/requirements.txt
  ```
- **Start Command**:
  ```bash
  python services/cloud-ai/server.py --port $PORT
  ```
- **Instance Type**: `Free` (0$/month)

---

### Step 4: Environment Variables (Security Key) Set Karein
Neeche **"Advanced"** ya **"Environment Variables"** section me jayein aur ek variable add karein:
- **Key**: `API_KEY`
- **Value**: `ak_sec_print_ai_2026`

---

### Step 5: "Deploy Web Service" par Click Karein
- Render apne aap dependencies install karega aur service start karega.
- 1-2 minute me status **"Live"** dikhayega.
- Upar aapko ek URL mil jayega, jaise:
  `https://akprintseva-ai.onrender.com`

Aap browser me `https://akprintseva-ai.onrender.com/health` khol kar check kar sakte hain, wahan aana chahiye:
```json
{"status": "healthy", "service": "AK Print Seva Cloud AI", "services_loaded": true}
```

---

## 🔗 Hostinger se Connect Kaise Karein?

Jab aapka Render URL live ho jaye:
1. Hostinger ke File Manager me jayein (`public_html/config.php`).
2. `config.php` me ye do line daal dein:
   ```php
   define('CLOUD_AI_URL', 'https://akprintseva-ai.onrender.com');
   define('CLOUD_AI_KEY', 'ak_sec_print_ai_2026');
   ```
3. Bas! Ab Hostinger par **Aadhaar Print**, **Smart Document Scanner**, aur **Multi-PDF Print Queue** cloud speed se 100% fast chalenge!

---

## 💡 Pro-Tip: Render Free Tier Cold-Start
Render ka free tier 15 minute tak koi user na aane par sleep mode me chala jata hai. Pehli request aane par yeh 20-30 second me wake up hota hai.
Isko 24/7 hamesha active rakhne ke liye aap [cron-job.org](https://cron-job.org) ya [uptimerobot.com](https://uptimerobot.com) par free account banakar har 10 minute me `https://akprintseva-ai.onrender.com/health` par ping set kar sakte hain — isse yeh **hamesha 1-second me instant respond** karega!
