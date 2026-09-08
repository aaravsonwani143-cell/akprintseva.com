<?php
/**
 * ═══════════════════════════════════════════════════════════════
 * AK PRINT SEVA — PVC Card Services Listing Studio
 * All PVC Card Types: Aadhaar, Voter, PAN, Ayushman, Farmer ID
 * ═══════════════════════════════════════════════════════════════
 */
$pageTitle = 'PVC Card Print & Home Delivery Service — Aadhaar, Voter, PAN, Ayushman | AK Print Seva';
$pageMetaDesc = 'Order original ATM-size PVC plastic cards online: Aadhaar PVC, Voter ID PVC, PAN PVC, Ayushman Bharat & Farmer ID. 300 DPI thermal print with SpeedPost delivery.';
$activeNav = 'pvc-cards';
require_once __DIR__ . '/../../includes/header.php';
require_once __DIR__ . '/../../includes/navbar.php';
?>

<style>
:root {
    --v-purple: #8B5CF6;
    --v-purple-dark: #7C3AED;
    --v-purple-light: #A78BFA;
    --v-purple-bg: rgba(139, 92, 246, 0.12);
    
    --v-orange: #FF6B00;
    --v-orange-dark: #E85D04;
    --v-orange-light: #FFA048;
    --v-orange-bg: rgba(255, 107, 0, 0.12);
    
    --v-blue: #3B82F6;
    --v-green: #10B981;
    --v-green-bg: rgba(16, 185, 129, 0.12);
    
    --v-bg: #F4F7FB;
    --v-surface: #FFFFFF;
    --v-border: #E2E8F0;
    --v-text-hi: #0F2744;
    --v-text-mid: #475569;
    --v-text-lo: #94A3B8;
    --v-radius: 16px;
    --v-radius-sm: 10px;
    --v-shadow: 0 6px 22px rgba(15, 39, 68, 0.07);
}

[data-theme="dark"] {
    --v-bg: #070D18;
    --v-surface: #0E1726;
    --v-border: rgba(255, 255, 255, 0.09);
    --v-text-hi: #F8FAFC;
    --v-text-mid: #94A3B8;
    --v-text-lo: #64748B;
    --v-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
}

.pvc-services-wrapper {
    background: var(--v-bg);
    color: var(--v-text-hi);
    min-height: 85vh;
    padding-bottom: 60px;
    font-family: 'Plus Jakarta Sans', sans-serif;
}

/* ═══ BREADCRUMB ═══ */
.breadcrumb-bar {
    padding: 14px 0 6px;
    font-size: 0.82rem;
    color: var(--v-text-mid);
    display: flex;
    align-items: center;
    gap: 6px;
}
.breadcrumb-bar a {
    color: var(--v-purple);
    text-decoration: none;
    font-weight: 700;
}
.breadcrumb-bar a:hover { text-decoration: underline; }
.breadcrumb-sep { opacity: 0.5; }

/* ═══ HERO SECTION ═══ */
.pvc-hero {
    position: relative;
    overflow: hidden;
    padding: 36px 20px 24px;
    text-align: center;
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.06) 0%, rgba(255, 107, 0, 0.05) 100%);
    border-bottom: 1px solid var(--v-border);
}
[data-theme="dark"] .pvc-hero {
    background: linear-gradient(180deg, rgba(14, 23, 38, 0.95) 0%, rgba(7, 13, 24, 0.98) 100%);
}

.hero-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--v-purple-bg);
    border: 1px solid rgba(139, 92, 246, 0.35);
    padding: 5px 16px;
    border-radius: 50px;
    font-size: 0.76rem;
    font-weight: 800;
    color: var(--v-purple);
    margin-bottom: 14px;
}
.pill-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--v-green);
    box-shadow: 0 0 8px var(--v-green);
}

.hero-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.3rem;
    font-weight: 900;
    color: var(--v-text-hi);
    line-height: 1.2;
    margin-bottom: 8px;
}
.hero-gradient-word {
    background: linear-gradient(135deg, #FF6B00 0%, #8B5CF6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
[data-theme="dark"] .hero-gradient-word {
    background: linear-gradient(135deg, #FFA048 0%, #A78BFA 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.hero-desc {
    color: var(--v-text-mid);
    font-size: 0.94rem;
    max-width: 660px;
    margin: 0 auto 20px;
    line-height: 1.55;
}

/* 🌟 TRUST HIGHLIGHT BADGES BAR */
.trust-badges-bar {
    display: flex;
    justify-content: center;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 14px;
}
.tb-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--v-surface);
    border: 1px solid var(--v-border);
    padding: 6px 14px;
    border-radius: 30px;
    font-size: 0.76rem;
    font-weight: 800;
    color: var(--v-text-hi);
    box-shadow: 0 2px 8px rgba(15, 39, 68, 0.04);
}

/* ═══ PVC CARDS GRID ═══ */
.pvc-cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 20px;
    margin: 36px 0 50px;
}

.pvc-card-studio {
    background: var(--v-surface);
    border: 1px solid var(--v-border);
    border-radius: var(--v-radius);
    overflow: hidden;
    text-decoration: none;
    color: inherit;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    flex-direction: column;
    box-shadow: var(--v-shadow);
    position: relative;
}
.pvc-card-studio:hover {
    transform: translateY(-5px);
    border-color: var(--card-accent, var(--v-purple));
    box-shadow: 0 14px 35px -8px rgba(139, 92, 246, 0.25);
}

.pvc-card-top-stripe {
    height: 4px;
    width: 100%;
    background: var(--card-gradient, linear-gradient(90deg, #8B5CF6, #FF6B00));
}

.pvc-card-body {
    padding: 24px 22px 20px;
    display: flex;
    flex-direction: column;
    flex: 1;
}

.pvc-card-header-row {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 14px;
}
.pvc-icon-bubble {
    width: 52px;
    height: 52px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.7rem;
    flex-shrink: 0;
    background: var(--card-tint, rgba(139, 92, 246, 0.12));
    border: 1.5px solid var(--card-border, rgba(139, 92, 246, 0.3));
}
.pvc-header-text { flex: 1; min-width: 0; }
.pvc-header-text h3 {
    font-size: 1.15rem;
    font-weight: 900;
    color: var(--v-text-hi);
    margin: 0 0 2px;
    line-height: 1.25;
}
.pvc-header-text .pvc-hi-name {
    font-size: 0.80rem;
    color: var(--v-text-mid);
    font-weight: 700;
}

.pvc-desc-block {
    font-size: 0.86rem;
    color: var(--v-text-mid);
    line-height: 1.55;
    margin-bottom: 16px;
    flex: 1;
}

.pvc-features-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 20px;
    padding: 10px 12px;
    background: var(--v-bg);
    border: 1px solid var(--v-border);
    border-radius: 8px;
}
.pfl-item {
    font-size: 0.76rem;
    font-weight: 700;
    color: var(--v-text-hi);
    display: flex;
    align-items: center;
    gap: 6px;
}

.pvc-footer-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid var(--v-border);
    padding-top: 16px;
    margin-top: auto;
}
.pvc-price-box {
    display: flex;
    flex-direction: column;
}
.pvc-price-number {
    font-size: 1.35rem;
    font-weight: 900;
    color: var(--card-accent, var(--v-purple));
    line-height: 1;
}
.pvc-price-sub {
    font-size: 0.70rem;
    font-weight: 700;
    color: var(--v-text-lo);
    margin-top: 3px;
}

.btn-order-cta {
    padding: 10px 20px;
    border-radius: 8px;
    font-size: 0.86rem;
    font-weight: 800;
    color: #ffffff;
    background: var(--card-gradient, linear-gradient(135deg, #8B5CF6, #FF6B00));
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15);
    transition: all 0.2s ease;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}
.pvc-card-studio:hover .btn-order-cta {
    transform: scale(1.04);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
}

/* ═══ B2B CYBER CAFE BANNER ═══ */
.b2b-partner-banner {
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.08) 0%, rgba(255, 107, 0, 0.08) 100%);
    border: 1.5px solid rgba(139, 92, 246, 0.35);
    border-radius: var(--v-radius);
    padding: 28px 30px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 20px;
    box-shadow: var(--v-shadow);
    margin-bottom: 50px;
}
.bpb-left { max-width: 650px; }
.bpb-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(255, 107, 0, 0.12);
    color: var(--v-orange);
    font-size: 0.74rem;
    font-weight: 800;
    padding: 3px 10px;
    border-radius: 20px;
    margin-bottom: 8px;
}
.bpb-title {
    font-size: 1.35rem;
    font-weight: 900;
    color: var(--v-text-hi);
    margin: 0 0 6px;
}
.bpb-desc {
    font-size: 0.86rem;
    color: var(--v-text-mid);
    line-height: 1.5;
    margin: 0;
}
.btn-partner-whatsapp {
    background: linear-gradient(135deg, #16A34A 0%, #15803D 100%);
    color: #fff;
    font-weight: 800;
    font-size: 0.90rem;
    padding: 12px 24px;
    border-radius: 10px;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    box-shadow: 0 4px 14px rgba(22, 163, 74, 0.35);
    white-space: nowrap;
}
.btn-partner-whatsapp:hover {
    transform: translateY(-2px);
    filter: brightness(1.08);
}

/* 🌟 HIGH-RANKING GOOGLE SEO SECTION */
.seo-guide-section {
  margin-top: 30px;
  padding-top: 30px;
  border-top: 1px solid var(--v-border);
}
.seo-features-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 30px;
}
.seo-feat-card {
  background: var(--v-surface);
  border: 1px solid var(--v-border);
  border-radius: var(--v-radius);
  padding: 16px;
  text-align: center;
  box-shadow: var(--v-shadow);
  transition: transform 0.2s ease;
}
.seo-feat-card:hover {
  transform: translateY(-3px);
  border-color: var(--v-purple);
}
.sfc-icon {
  font-size: 1.8rem;
  margin-bottom: 8px;
}
.sfc-title {
  font-size: 0.90rem;
  font-weight: 800;
  color: var(--v-text-hi);
  margin-bottom: 4px;
}
.sfc-desc {
  font-size: 0.74rem;
  color: var(--v-text-mid);
  line-height: 1.4;
}

.seo-article-block {
  background: var(--v-surface);
  border: 1px solid var(--v-border);
  border-radius: var(--v-radius);
  padding: 24px;
  box-shadow: var(--v-shadow);
}
.seo-h2 {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--v-text-hi);
  margin-bottom: 10px;
}
.seo-article-block p {
  font-size: 0.84rem;
  color: var(--v-text-mid);
  line-height: 1.6;
  margin-bottom: 16px;
}
.seo-h3 {
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--v-text-hi);
  margin: 20px 0 12px;
}
.seo-faq-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 24px;
}
.faq-item {
  background: var(--v-bg);
  border: 1px solid var(--v-border);
  border-radius: 8px;
  padding: 12px 14px;
}
.faq-q {
  font-size: 0.82rem;
  font-weight: 800;
  color: var(--v-text-hi);
  margin-bottom: 4px;
}
.faq-a {
  font-size: 0.76rem;
  color: var(--v-text-mid);
  line-height: 1.45;
  margin: 0;
}

/* 🏷️ SEO TAGS CLOUD */
.seo-tags-cloud-wrap {
  border-top: 1px solid var(--v-border);
  padding-top: 16px;
  margin-top: 20px;
}
.seo-tags-title {
  font-size: 0.80rem;
  font-weight: 800;
  color: var(--v-text-hi);
  margin-bottom: 10px;
}
.seo-tags-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.seo-tag {
  background: var(--v-bg);
  border: 1px solid var(--v-border);
  color: var(--v-text-mid);
  font-size: 0.72rem;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 14px;
  transition: all 0.15s ease;
}
.seo-tag:hover {
  background: var(--v-purple-bg);
  color: var(--v-purple);
  border-color: var(--v-purple);
}

@media (max-width: 900px) {
    .pvc-cards-grid { grid-template-columns: 1fr; }
    .b2b-partner-banner { flex-direction: column; align-items: flex-start; }
    .seo-features-grid { grid-template-columns: 1fr 1fr; }
    .seo-faq-grid { grid-template-columns: 1fr; }
}
</style>

<div class="pvc-services-wrapper">

    <!-- BREADCRUMB -->
    <div class="container">
        <div class="breadcrumb-bar">
            <a href="/index.php">🏠 Home</a>
            <span class="breadcrumb-sep">›</span>
            <span>PVC Card Services Studio</span>
        </div>
    </div>

    <!-- HERO SECTION -->
    <section class="pvc-hero">
        <div class="container">
            <div class="hero-pill">
                <span class="pill-dot"></span>
                <span>✨ 100% Original PVC Plastic · ATM Size · India Post SpeedPost Home Delivery</span>
            </div>
            <h1 class="hero-title">
                PVC Card <span class="hero-gradient-word">Print &amp; Delivery Studio</span>
            </h1>
            <p class="hero-desc">
                Aadhaar, Voter ID, PAN, Ayushman व Farmer ID कार्ड को ओरिजिनल ATM साइज़ प्लास्टिक PVC में प्रिंट करवाएं। सिर्फ़ <strong>₹99</strong> में स्पीड पोस्ट होम डिलीवरी सहित।
            </p>

            <div class="trust-badges-bar">
                <div class="tb-pill">💳 Official ATM Size (CR80)</div>
                <div class="tb-pill">🛡️ 100% Waterproof &amp; Scratchproof</div>
                <div class="tb-pill">⚡ 24-Hour Dispatch Guarantee</div>
                <div class="tb-pill">🚚 SpeedPost Live Consignment Tracking</div>
            </div>
        </div>
    </section>

    <!-- MAIN CARDS CONTAINER -->
    <main class="container">

        <!-- 🖨️ PVC CARDS GRID -->
        <div class="pvc-cards-grid">
            <?php
            foreach ($PVC_CARD_TYPES as $key => $card):
                $g1 = $card['gradient'][0];
                $g2 = $card['gradient'][1];
                $accentColor = $g1;
            ?>
            <a href="<?php echo htmlspecialchars($card['url']); ?>" class="pvc-card-studio" 
               style="--card-accent:<?php echo $accentColor; ?>; --card-gradient:linear-gradient(135deg, <?php echo $g1; ?> 0%, <?php echo $g2; ?> 100%); --card-tint:<?php echo $g1; ?>18; --card-border:<?php echo $g1; ?>44;">
                
                <div class="pvc-card-top-stripe"></div>

                <div class="pvc-card-body">
                    <div class="pvc-card-header-row">
                        <div class="pvc-icon-bubble">
                            <?php echo $card['icon']; ?>
                        </div>
                        <div class="pvc-header-text">
                            <h3><?php echo htmlspecialchars($card['name']); ?></h3>
                            <div class="pvc-hi-name"><?php echo $card['name_hi']; ?></div>
                        </div>
                    </div>

                    <div class="pvc-desc-block">
                        <?php echo $card['description']; ?>
                    </div>

                    <div class="pvc-features-list">
                        <div class="pfl-item">✅ 300 DPI High-Definition Thermal Print</div>
                        <div class="pfl-item">✅ Ultra-Durable 0.76mm Rigid Plastic</div>
                        <div class="pfl-item">✅ SpeedPost Dispatched with Tracking</div>
                    </div>

                    <div class="pvc-footer-row">
                        <div class="pvc-price-box">
                            <span class="pvc-price-number">₹<?php echo $card['price']; ?></span>
                            <span class="pvc-price-sub">SpeedPost डिलीवरी सहित</span>
                        </div>
                        <span class="btn-order-cta">
                            Order Now ➔
                        </span>
                    </div>
                </div>
            </a>
            <?php endforeach; ?>
        </div>

        <!-- 🤝 CSC & CYBER CAFE B2B PARTNER BANNER -->
        <div class="b2b-partner-banner">
            <div class="bpb-left">
                <div class="bpb-pill">💼 CSC &amp; Cyber Cafe Partner Hub</div>
                <h3 class="bpb-title">क्या आप डिजिटल सेवा केंद्र या साइबर कैफे चलाते हैं?</h3>
                <p class="bpb-desc">
                    थोक (Bulk) PVC कार्ड प्रिंटिंग पर विशेष डिस्काउंट पाएं और अपने ग्राहकों के कार्ड सीधे अपने पते पर प्रायोरिटी स्पीड पोस्ट से मंगवाएं।
                </p>
            </div>
            <a href="https://wa.me/919999999999?text=Hello%20AK%20Print%20Seva,%20I%20want%20bulk%20PVC%20card%20printing%20rates" target="_blank" class="btn-partner-whatsapp">
                💬 बल्क रेट्स हेतु चैट करें ➔
            </a>
        </div>

        <!-- 🌟 HIGH-RANKING GOOGLE SEO & USER GUIDE SECTION -->
        <section class="seo-guide-section">
            
            <!-- Features Grid (4 Pillars) -->
            <div class="seo-features-grid">
                <div class="seo-feat-card">
                    <div class="sfc-icon">💳</div>
                    <div class="sfc-title">Original CR80 ATM Size</div>
                    <div class="sfc-desc">Exact dimensions (85.6mm × 54mm) with rounded smooth edges designed to fit inside standard wallets.</div>
                </div>
                <div class="seo-feat-card">
                    <div class="sfc-icon">🛡️</div>
                    <div class="sfc-title">Double-Sided Lamination</div>
                    <div class="sfc-desc">Protective thermal gloss laminate shields barcodes and QR codes from moisture, fading, and scratches.</div>
                </div>
                <div class="seo-feat-card">
                    <div class="sfc-icon">🚚</div>
                    <div class="sfc-title">India Post SpeedPost</div>
                    <div class="sfc-desc">Safe, secure pan-India doorstep delivery with official consignment tracking number provided within 24 hours.</div>
                </div>
                <div class="seo-feat-card">
                    <div class="sfc-icon">🔒</div>
                    <div class="sfc-title">100% Privacy &amp; Security</div>
                    <div class="sfc-desc">Your uploaded identity PDFs are processed with end-to-end encryption and permanently auto-deleted post printing.</div>
                </div>
            </div>

            <!-- SEO Editorial Content -->
            <article class="seo-article-block">
                <h2 class="seo-h2">Online PVC Card Printing &amp; Fast Home Delivery Service Across India</h2>
                <p>
                    AK Print Seva is India's leading platform for online PVC plastic card printing. We specialize in converting government identity PDFs (such as e-Aadhaar, Voter ID EPIC, e-PAN, and Ayushman PMJAY Golden Cards) into high-definition, bank ATM-grade rigid plastic cards.
                </p>
                <p>
                    Tired of fragile paper laminations tearing in your pocket? Our 0.76mm thick CR80 PVC cards are completely waterproof, scratch-resistant, and verified for official use across banks, airports, SIM verification centers, and government offices.
                </p>

                <h3 class="seo-h3">Frequently Asked Questions (FAQs)</h3>
                <div class="seo-faq-grid">
                    <div class="faq-item">
                        <div class="faq-q">Q1. What is the cost of printing a PVC card?</div>
                        <p class="faq-a">A single PVC card is just ₹99 with all-inclusive India Post SpeedPost doorstep delivery and zero hidden charges.</p>
                    </div>
                    <div class="faq-item">
                        <div class="faq-q">Q2. How do I order my Aadhaar or Voter PVC Card?</div>
                        <p class="faq-a">Click on your desired card above, upload your official government PDF file, fill in your delivery address, and pay securely via UPI/Card through Razorpay.</p>
                    </div>
                    <div class="faq-item">
                        <div class="faq-q">Q3. When will my PVC card be dispatched?</div>
                        <p class="faq-a">Orders are printed, laminated, and handed over to India Post within 24 hours. You receive an instant SpeedPost tracking number via SMS.</p>
                    </div>
                    <div class="faq-item">
                        <div class="faq-q">Q4. Are these PVC cards valid for official identity checks?</div>
                        <p class="faq-a">Yes. All cards feature high-resolution 300 DPI graphics, crisp barcodes, and scannable QR codes valid for all identity verification purposes.</p>
                    </div>
                </div>

                <!-- Search Keywords Tag Cloud -->
                <div class="seo-tags-cloud-wrap">
                    <div class="seo-tags-title">Popular Related Searches</div>
                    <div class="seo-tags-cloud">
                        <span class="seo-tag">Aadhaar PVC Card Online Apply</span>
                        <span class="seo-tag">Voter ID Plastic Card Print</span>
                        <span class="seo-tag">PAN Card PVC Delivery</span>
                        <span class="seo-tag">Ayushman Bharat Golden Card PVC</span>
                        <span class="seo-tag">Farmer ID Card PVC Print</span>
                        <span class="seo-tag">Speed Post PVC Card Tracking</span>
                        <span class="seo-tag">Cyber Cafe PVC Card Partner</span>
                    </div>
                </div>
            </article>

        </section>

    </main>

</div>

<?php require_once __DIR__ . '/../../includes/footer.php'; ?>
