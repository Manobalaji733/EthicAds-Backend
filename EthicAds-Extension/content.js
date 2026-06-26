// ==========================================
// CONFIGURATION & ENDPOINTS
// ==========================================
const WORKFLOW_URL = "https://ethicads-backend.onrender.com/api/v1/workflows/run";
const CLICK_PROXY_URL = "https://ethicads-backend.onrender.com/api/v1/clicks";

const API_KEY = "college_hackathon_demo_key_123"; 

async function getOrCreateDeviceID() {
    return new Promise((resolve) => {
        chrome.storage.local.get(["device_id"], (result) => {
            if (result.device_id) {
                resolve(result.device_id);
            } else {
                const newId = "dev_" + Math.random().toString(36).substring(2, 15);
                chrome.storage.local.set({ device_id: newId }, () => {
                    resolve(newId);
                });
            }
        });
    });
}

// ==========================================
// CORE ENGINE PIPELINE
// ==========================================
async function runAdEnginePipeline() {
    try {
        const deviceId = await getOrCreateDeviceID();
        
        const pageText = document.body.innerText || "";
        const cleanText = pageText.substring(0, 4000); 

        if (cleanText.trim().length < 10) return;

        const payload = {
            raw_viewport_text: cleanText,
            device_id: deviceId
        };

        console.log(`[EthicAds] Scanning context... Sending to cloud.`);
        
        const response = await fetch(WORKFLOW_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "x-api-key": API_KEY 
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            console.error(`[EthicAds] API Error: ${response.status}`);
            return;
        }

        const data = await response.json();
        console.log("[EthicAds] Live Products Received:", data);

        if (data.status === "success" && data.ads && data.ads.length > 0) {
            injectProWidget(data.ads, deviceId);
        }
    } catch (error) {
        console.error("[EthicAds] Fatal content script error:", error);
    }
}

// ==========================================
// PRO UI/UX "PEEK-A-BOO" INJECTION
// ==========================================
function injectProWidget(adsArray, deviceId) {
    if (document.getElementById("ethicads-pro-root")) return;

    // 1. Create the Root Invisible Container
    const root = document.createElement("div");
    root.id = "ethicads-pro-root";
    root.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 2147483647;
        font-family: system-ui, -apple-system, sans-serif;
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        pointer-events: none; /* Let clicks pass through empty space */
    `;

    // 2. Create the Minimized "Peek-a-boo" Button (FAB)
    const fab = document.createElement("div");
    fab.id = "ethicads-fab";
    fab.style.cssText = `
        width: 48px;
        height: 48px;
        background: linear-gradient(135deg, #16a34a, #15803d);
        border-radius: 50%;
        box-shadow: 0 10px 15px -3px rgba(22, 163, 74, 0.3), 0 4px 6px -4px rgba(22, 163, 74, 0.3);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        color: white;
        transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.3s ease;
        pointer-events: auto;
        opacity: 0;
        transform: scale(0.5) translateY(20px);
        position: absolute;
        bottom: 0;
        right: 0;
    `;
    fab.innerHTML = "🌱";
    fab.title = "View EthicAds Matches";

    // 3. Create the Expanded Panel
    const panel = document.createElement("div");
    panel.id = "ethicads-panel";
    panel.style.cssText = `
        width: 360px;
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(226, 232, 240, 0.8);
        border-radius: 20px;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(0,0,0,0.02);
        overflow: hidden;
        transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
        pointer-events: auto;
        opacity: 0;
        transform: translateY(30px) scale(0.95);
        transform-origin: bottom right;
        margin-bottom: 60px; /* Space for the FAB to sit under it if needed, though they morph */
        display: none;
    `;

    // 4. Build the Glassy Header
    const headerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; background: rgba(248, 250, 252, 0.7); border-bottom: 1px solid rgba(226, 232, 240, 0.8);">
            <div style="font-size: 13px; font-weight: 800; color: #15803d; text-transform: uppercase; letter-spacing: 0.08em; display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 16px;">🌱</span> EthicAds Verified
            </div>
            <button id="ethicads-minimize-btn" title="Minimize" style="background: rgba(226, 232, 240, 0.5); border: none; cursor: pointer; color: #475569; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; transition: all 0.2s ease;" onmouseover="this.style.background='rgba(203, 213, 225, 0.8)'; this.style.color='#0f172a'" onmouseout="this.style.background='rgba(226, 232, 240, 0.5)'; this.style.color='#475569'">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
            </button>
        </div>
    `;

    // 5. Build the Product List
    let productListHTML = `<div style="padding: 16px 20px; display: flex; flex-direction: column; gap: 14px;">`;
    
    adsArray.forEach(ad => {
        const secureClickUrl = `${CLICK_PROXY_URL}?ad_id=${encodeURIComponent(ad.id)}&dest=${encodeURIComponent(ad.url)}&device_id=${encodeURIComponent(deviceId)}`;
        const imgUrl = ad.image || "https://via.placeholder.com/60?text=Eco";

        productListHTML += `
            <a href="${secureClickUrl}" target="_blank" style="display: flex; align-items: center; gap: 14px; text-decoration: none; padding: 10px; border-radius: 12px; background: rgba(255,255,255,0.5); border: 1px solid transparent; transition: all 0.2s ease;" onmouseover="this.style.backgroundColor='#ffffff'; this.style.borderColor='#e2e8f0'; this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 6px -1px rgba(0, 0, 0, 0.05)';" onmouseout="this.style.backgroundColor='rgba(255,255,255,0.5)'; this.style.borderColor='transparent'; this.style.transform='translateY(0)'; this.style.boxShadow='none';">
                <div style="width: 56px; height: 56px; border-radius: 10px; background: #ffffff; border: 1px solid #e2e8f0; display: flex; align-items: center; justify-content: center; overflow: hidden; flex-shrink: 0;">
                    <img src="${imgUrl}" style="max-width: 100%; max-height: 100%; object-fit: contain;">
                </div>
                <div style="display: flex; flex-direction: column; gap: 4px; min-width: 0;">
                    <div style="font-size: 13.5px; font-weight: 600; color: #1e293b; line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                        ${ad.title}
                    </div>
                    <div style="font-size: 14px; font-weight: 800; color: #16a34a;">
                        ${ad.price}
                    </div>
                </div>
            </a>
        `;
    });
    
    productListHTML += `</div>`;

    // 6. Assemble the Widget
    panel.innerHTML = headerHTML + productListHTML;
    root.appendChild(panel);
    root.appendChild(fab);
    document.body.appendChild(root);

    // 7. Peek-a-boo Animation Logic
    let isExpanded = false;

    const toggleWidget = (expand) => {
        isExpanded = expand;
        if (isExpanded) {
            // Morph into Panel
            panel.style.display = 'block';
            setTimeout(() => {
                panel.style.opacity = '1';
                panel.style.transform = 'translateY(0) scale(1)';
                panel.style.pointerEvents = 'auto';
                
                fab.style.opacity = '0';
                fab.style.transform = 'scale(0.5) translateY(20px)';
                fab.style.pointerEvents = 'none';
            }, 10);
        } else {
            // Morph into FAB (Floating Button)
            panel.style.opacity = '0';
            panel.style.transform = 'translateY(30px) scale(0.95)';
            panel.style.pointerEvents = 'none';
            
            fab.style.opacity = '1';
            fab.style.transform = 'scale(1) translateY(0)';
            fab.style.pointerEvents = 'auto';
            
            setTimeout(() => {
                if (!isExpanded) panel.style.display = 'none';
            }, 500); 
        }
    };

    // Attach Listeners
    document.getElementById('ethicads-minimize-btn').addEventListener('click', () => toggleWidget(false));
    fab.addEventListener('click', () => toggleWidget(true));
    
    // Add subtle hover effect to the FAB
    fab.addEventListener('mouseover', () => { if(!isExpanded) fab.style.transform = 'scale(1.08) translateY(0)'; });
    fab.addEventListener('mouseout', () => { if(!isExpanded) fab.style.transform = 'scale(1) translateY(0)'; });

    // Initial state: Start closed (Peek-a-boo style), then pop out!
    setTimeout(() => toggleWidget(true), 300);
}

// Start the engine
runAdEnginePipeline();