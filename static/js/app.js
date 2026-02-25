/* ═══════════════════════════════════════════════════════════════════════════
   $SoLARP – Frontend App
   Particles, data fetching, animations, interactions
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
    "use strict";

    // ─── CONFIG ──────────────────────────────────────────────────────────────
    const API_URL = "/api/stats";
    const REFRESH_INTERVAL = 30_000; // 30s

    // ─── PARTICLES ───────────────────────────────────────────────────────────
    const canvas = document.getElementById("particles");
    const ctx = canvas.getContext("2d");
    let particles = [];
    let mouseX = -1000, mouseY = -1000;

    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }

    class Particle {
        constructor() {
            this.reset();
        }
        reset() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.size = Math.random() * 2 + 0.5;
            this.speedX = (Math.random() - 0.5) * 0.4;
            this.speedY = (Math.random() - 0.5) * 0.4;
            this.opacity = Math.random() * 0.5 + 0.1;
            this.color = Math.random() > 0.5 ? "153,69,255" : "20,241,149";
        }
        update() {
            this.x += this.speedX;
            this.y += this.speedY;

            // Mouse interaction
            const dx = this.x - mouseX;
            const dy = this.y - mouseY;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 120) {
                this.x += dx * 0.02;
                this.y += dy * 0.02;
                this.opacity = Math.min(this.opacity + 0.02, 0.8);
            }

            if (this.x < 0 || this.x > canvas.width ||
                this.y < 0 || this.y > canvas.height) {
                this.reset();
            }
        }
        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${this.color}, ${this.opacity})`;
            ctx.fill();
        }
    }

    function initParticles() {
        resizeCanvas();
        const count = Math.min(Math.floor((canvas.width * canvas.height) / 12000), 150);
        particles = [];
        for (let i = 0; i < count; i++) {
            particles.push(new Particle());
        }
    }

    function drawLines() {
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 120) {
                    ctx.beginPath();
                    ctx.strokeStyle = `rgba(153, 69, 255, ${0.06 * (1 - dist / 120)})`;
                    ctx.lineWidth = 0.5;
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.stroke();
                }
            }
        }
    }

    function animateParticles() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles.forEach(p => {
            p.update();
            p.draw();
        });
        drawLines();
        requestAnimationFrame(animateParticles);
    }

    window.addEventListener("resize", () => {
        resizeCanvas();
        initParticles();
    });

    document.addEventListener("mousemove", (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
    });

    initParticles();
    animateParticles();

    // ─── NAV ─────────────────────────────────────────────────────────────────
    const nav = document.querySelector(".nav");
    const mobileToggle = document.getElementById("mobileToggle");
    const navLinks = document.querySelector(".nav-links");

    window.addEventListener("scroll", () => {
        nav.classList.toggle("scrolled", window.scrollY > 60);
    });

    if (mobileToggle) {
        mobileToggle.addEventListener("click", () => {
            navLinks.classList.toggle("open");
        });

        navLinks.querySelectorAll("a").forEach(a => {
            a.addEventListener("click", () => navLinks.classList.remove("open"));
        });
    }

    // ─── SCROLL ANIMATIONS ──────────────────────────────────────────────────
    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const delay = entry.target.getAttribute("data-delay") || 0;
                    setTimeout(() => {
                        entry.target.classList.add("visible");
                    }, parseInt(delay));
                }
            });
        },
        { threshold: 0.1 }
    );

    document.querySelectorAll(".feature-card").forEach(card => observer.observe(card));

    // ─── COUNTER ANIMATION ──────────────────────────────────────────────────
    function animateValue(el, start, end, duration, decimals = 0, prefix = "", suffix = "") {
        const startTime = performance.now();
        const diff = end - start;

        function tick(now) {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // ease out cubic
            const current = start + diff * eased;

            el.textContent = prefix + current.toFixed(decimals) + suffix;

            if (progress < 1) {
                requestAnimationFrame(tick);
            }
        }

        requestAnimationFrame(tick);
    }

    // ─── TICKER BAR ─────────────────────────────────────────────────────────
    function buildTicker(data) {
        const track = document.getElementById("tickerTrack");
        if (!track) return;

        const items = [];

        // Add recent trades to ticker
        if (data.recent_trades && data.recent_trades.length > 0) {
            data.recent_trades.forEach(t => {
                const cls = t.pnl_sol >= 0 ? "positive" : "negative";
                const sign = t.pnl_sol >= 0 ? "+" : "";
                items.push(
                    `<span class="ticker-item">
                        <span class="symbol">$${t.symbol}</span>
                        <span class="${cls}">${t.multiplier}x</span>
                        <span class="${cls}">${sign}${t.pnl_sol.toFixed(4)} SOL</span>
                    </span>`
                );
            });
        }

        // Add open positions
        if (data.open_positions && data.open_positions.length > 0) {
            data.open_positions.forEach(p => {
                items.push(
                    `<span class="ticker-item">
                        <span class="symbol">$${p.symbol}</span>
                        <span>OPEN</span>
                        <span>${p.sol_invested.toFixed(2)} SOL</span>
                    </span>`
                );
            });
        }

        // Default items if nothing yet
        if (items.length === 0) {
            const defaults = [
                "$SoLARP — LIVE PAPER TRADING BOT",
                "🦍 scanning for memecoins...",
                "24/7 automated degen",
                "zero real money, pure alpha",
                "join telegram for signals",
            ];
            defaults.forEach(d => {
                items.push(`<span class="ticker-item">${d}</span>`);
            });
        }

        // Double for seamless scroll
        const html = items.join("") + items.join("");
        track.innerHTML = html;
    }

    // ─── DATA FETCHING ──────────────────────────────────────────────────────
    let lastData = null;

    async function fetchStats() {
        try {
            const res = await fetch(API_URL);
            if (!res.ok) throw new Error("API error");
            const data = await res.json();
            updateDashboard(data);
            lastData = data;
        } catch (e) {
            console.warn("Could not fetch stats:", e);
            // Show demo data
            if (!lastData) {
                updateDashboard(getDemoData());
            }
        }
    }

    async function fetchFeed() {
        try {
            const res = await fetch("/api/feed");
            if (!res.ok) return;
            const feed = await res.json();
            renderFeed(feed);
        } catch (e) {
            console.warn("Could not fetch feed:", e);
        }
    }

    function renderFeed(feed) {
        const container = document.getElementById("tradesFeed");
        if (!container) return;
        if (!feed || feed.length === 0) return;

        const kindIcon = { buy: "🟢", sell: "🔴", partial_sell: "💰", stop_loss: "🛑", dca: "📉", thought: "🧠", summary: "📊", trade: "📊" };
        const kindLabel = { buy: "BUY", sell: "SELL", partial_sell: "PARTIAL", stop_loss: "STOP", dca: "DCA", thought: "THOUGHT", summary: "SUMMARY", trade: "TRADE" };
        const kindColor = { buy: "#14F195", sell: "#FF4757", partial_sell: "#FFD700", stop_loss: "#FF4757", dca: "#9945FF", thought: "#64b5f6", summary: "#9945FF", trade: "#14F195" };

        container.innerHTML = feed.map((entry, i) => {
            const icon = kindIcon[entry.kind] || "📊";
            const label = kindLabel[entry.kind] || "MSG";
            const color = kindColor[entry.kind] || "#14F195";
            const ago = formatTimeAgo(entry.timestamp);
            // format text: newlines → <br>, preserve as monospace-ish
            const formatted = entry.text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/\n/g, "<br>");

            return `
                <div class="trade-card feed-card" style="animation-delay:${i * 40}ms; align-items:flex-start;">
                    <div class="trade-card-icon" style="font-size:1.4rem; min-width:44px; text-align:center;">${icon}</div>
                    <div class="trade-card-info" style="flex:1; min-width:0;">
                        <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
                            <span style="font-size:.65rem; font-weight:700; letter-spacing:.08em; color:${color}; background:${color}18; border:1px solid ${color}40; border-radius:4px; padding:2px 7px;">${label}</span>
                            <span style="font-size:.72rem; color:var(--text-muted);">${ago}</span>
                        </div>
                        <p style="font-size:.82rem; line-height:1.6; color:var(--text-secondary); margin:0; word-break:break-word;">${formatted}</p>
                    </div>
                </div>
            `;
        }).join("");
    }

    function getDemoData() {
        return {
            balance_sol: 10.0,
            total_balance_sol: 10.0,
            starting_balance: 10.0,
            overall_pnl_sol: 0.0,
            overall_pnl_pct: 0.0,
            closed_pnl_sol: 0.0,
            total_trades: 0,
            open_positions_count: 0,
            win_rate: 0.0,
            best_multiplier: 0.0,
            open_positions: [],
            recent_trades: [],
        };
    }

    function updateDashboard(data) {
        // Hero stats
        const heroBalance = document.getElementById("heroBalance");
        const heroTrades = document.getElementById("heroTrades");
        const heroWinRate = document.getElementById("heroWinRate");
        const heroPnl = document.getElementById("heroPnl");

        if (heroBalance) animateValue(heroBalance, 0, data.total_balance_sol, 1200, 4);
        if (heroTrades) animateValue(heroTrades, 0, data.total_trades, 800, 0);
        if (heroWinRate) animateValue(heroWinRate, 0, data.win_rate, 1000, 1, "", "%");
        if (heroPnl) {
            const prefix = data.overall_pnl_sol >= 0 ? "+" : "";
            animateValue(heroPnl, 0, data.overall_pnl_sol, 1000, 4, prefix);
            heroPnl.style.color = data.overall_pnl_sol >= 0 ? "#14F195" : "#FF4757";
        }

        // Main stats
        const statBalance = document.getElementById("statBalance");
        const statPnl = document.getElementById("statPnl");
        const statPnlPct = document.getElementById("statPnlPct");
        const statWinRate = document.getElementById("statWinRate");
        const statTrades = document.getElementById("statTrades");
        const statOpen = document.getElementById("statOpen");
        const statBest = document.getElementById("statBest");
        const balanceBar = document.getElementById("balanceBar");

        if (statBalance) {
            statBalance.textContent = data.total_balance_sol.toFixed(4);
        }
        if (statPnl) {
            const sign = data.overall_pnl_sol >= 0 ? "+" : "";
            statPnl.textContent = sign + data.overall_pnl_sol.toFixed(4);
            statPnl.className = "stat-value " + (data.overall_pnl_sol >= 0 ? "positive" : "negative");
        }
        if (statPnlPct) {
            const sign = data.overall_pnl_pct >= 0 ? "+" : "";
            statPnlPct.textContent = sign + data.overall_pnl_pct.toFixed(2);
            statPnlPct.className = "stat-value " + (data.overall_pnl_pct >= 0 ? "positive" : "negative");
        }
        if (statWinRate) statWinRate.textContent = data.win_rate.toFixed(1);
        if (statTrades) statTrades.textContent = data.total_trades;
        if (statOpen) statOpen.textContent = data.open_positions_count;
        if (statBest) statBest.textContent = data.best_multiplier > 0 ? data.best_multiplier.toFixed(2) + "x" : "—";
        if (balanceBar) {
            const pct = Math.min(Math.max((data.total_balance_sol / data.starting_balance) * 50, 5), 100);
            balanceBar.style.width = pct + "%";
        }

        // Open positions table
        const posSection = document.getElementById("positionsSection");
        const posBody = document.getElementById("positionsBody");
        if (data.open_positions && data.open_positions.length > 0 && posSection && posBody) {
            posSection.style.display = "block";
            posBody.innerHTML = data.open_positions.map(p => `
                <tr>
                    <td style="color: var(--text-bright); font-weight: 600;">$${p.symbol}</td>
                    <td>${formatPrice(p.entry_price_usd)}</td>
                    <td>${p.sol_invested.toFixed(3)}</td>
                    <td>${formatAge(p.age_hours)}</td>
                    <td>${p.dca_done ? '<span class="badge badge-dca">DCA\'d</span>' : '—'}</td>
                    <td><span class="badge badge-active">OPEN</span> ${p.partial_sold ? '<span class="badge badge-partial">Partial</span>' : ''}</td>
                </tr>
            `).join("");
        } else if (posSection) {
            posSection.style.display = "none";
        }

        // Recent trades feed
        const feed = document.getElementById("tradesFeed");
        if (feed && data.recent_trades && data.recent_trades.length > 0) {
            feed.innerHTML = data.recent_trades.map((t, i) => {
                const isWin = t.pnl_sol >= 0;
                const icon = getTradeIcon(t.reason);
                const iconClass = getTradeIconClass(t.reason);
                const pnlClass = isWin ? "positive" : "negative";
                const pnlSign = isWin ? "+" : "";
                const tag = getTradeTag(t.reason);
                const timeAgo = formatTimeAgo(t.timestamp);

                return `
                    <div class="trade-card" style="animation-delay: ${i * 60}ms">
                        <div class="trade-card-icon ${iconClass}">${icon}</div>
                        <div class="trade-card-info">
                            <h4>$${t.symbol} ${tag}</h4>
                            <p>${t.multiplier}x · ${timeAgo}</p>
                        </div>
                        <div class="trade-card-pnl ${pnlClass}">
                            ${pnlSign}${t.pnl_sol.toFixed(4)} SOL
                        </div>
                    </div>
                `;
            }).join("");
        }

        // Ticker
        buildTicker(data);
    }

    // ─── HELPERS ─────────────────────────────────────────────────────────────
    function formatPrice(price) {
        if (price < 0.000001) return "$" + price.toFixed(10);
        if (price < 0.001) return "$" + price.toFixed(8);
        if (price < 1) return "$" + price.toFixed(6);
        return "$" + price.toFixed(4);
    }

    function formatAge(hours) {
        if (hours < 1) return Math.round(hours * 60) + "m";
        if (hours < 24) return Math.round(hours) + "h";
        return Math.round(hours / 24) + "d " + Math.round(hours % 24) + "h";
    }

    function formatTimeAgo(timestamp) {
        if (!timestamp) return "";
        const diff = (Date.now() / 1000) - timestamp;
        if (diff < 60) return "just now";
        if (diff < 3600) return Math.floor(diff / 60) + "m ago";
        if (diff < 86400) return Math.floor(diff / 3600) + "h ago";
        return Math.floor(diff / 86400) + "d ago";
    }

    function getTradeIcon(reason) {
        switch (reason) {
            case "TP": return "💰";
            case "SL": return "🔴";
            case "JEET": return "🏃";
            case "STALE": return "🥱";
            default: return "📊";
        }
    }

    function getTradeIconClass(reason) {
        switch (reason) {
            case "TP": return "sell";
            case "SL": return "loss";
            case "JEET": return "jeet";
            case "STALE": return "stale";
            default: return "sell";
        }
    }

    function getTradeTag(reason) {
        switch (reason) {
            case "TP": return '<span class="tag tag-tp">Take Profit</span>';
            case "SL": return '<span class="tag tag-sl">Stop Loss</span>';
            case "JEET": return '<span class="tag tag-jeet">Jeet</span>';
            case "STALE": return '<span class="tag tag-stale">Stale</span>';
            default: return "";
        }
    }

    // ─── SMOOTH ANCHOR SCROLL ────────────────────────────────────────────────
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener("click", function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute("href"));
            if (target) {
                const offset = 80; // nav height
                const top = target.getBoundingClientRect().top + window.scrollY - offset;
                window.scrollTo({ top, behavior: "smooth" });
            }
        });
    });

    // ─── INIT ────────────────────────────────────────────────────────────────
    fetchStats();
    fetchFeed();
    setInterval(fetchStats, REFRESH_INTERVAL);
    setInterval(fetchFeed, REFRESH_INTERVAL);

    // Easter egg: Konami code → rain of apes
    let konamiSeq = [];
    const konamiCode = [38, 38, 40, 40, 37, 39, 37, 39, 66, 65];
    document.addEventListener("keydown", (e) => {
        konamiSeq.push(e.keyCode);
        if (konamiSeq.length > konamiCode.length) konamiSeq.shift();
        if (konamiSeq.join(",") === konamiCode.join(",")) {
            apeRain();
            konamiSeq = [];
        }
    });

    function apeRain() {
        for (let i = 0; i < 30; i++) {
            const ape = document.createElement("div");
            ape.textContent = "🦍";
            ape.style.cssText = `
                position: fixed;
                top: -50px;
                left: ${Math.random() * 100}vw;
                font-size: ${Math.random() * 30 + 20}px;
                z-index: 99999;
                pointer-events: none;
                animation: apefall ${Math.random() * 3 + 2}s linear forwards;
            `;
            document.body.appendChild(ape);
            setTimeout(() => ape.remove(), 5000);
        }

        // Inject keyframes if not already present
        if (!document.getElementById("apefall-style")) {
            const style = document.createElement("style");
            style.id = "apefall-style";
            style.textContent = `
                @keyframes apefall {
                    to { transform: translateY(110vh) rotate(720deg); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
    }

})();
