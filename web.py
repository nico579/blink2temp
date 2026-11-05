"""Serveur web local et tableau de bord pour blink2temp.

Fournit une interface web moderne, réactive et autonome (sans dépendance CDN)
avec affichage des températures actuelles, graphiques d'évolution et API REST,
avec zoom molette souris sur les plages de dates et déplacement transversal
(pan / scroll) à la souris sur l'axe temporel.
"""

from __future__ import annotations

import asyncio
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
import urllib.parse
from typing import Any

import collector
import config
import paths
from storage import Storage
import updater

HTML_PAGE = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Blink2Temp - Surveillance Températures Extérieures</title>
    <style>
        :root {
            --bg-color: #0b1120;
            --card-bg: #1e293b;
            --card-border: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #38bdf8;
            --primary-hover: #0284c7;
            --accent-green: #22c55e;
            --accent-orange: #f59e0b;
            --accent-red: #ef4444;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: var(--font-family);
            line-height: 1.5;
            padding: 24px 16px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
            margin-bottom: 28px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--card-border);
        }
        .title-block h1 {
            font-size: 1.75rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
            color: var(--primary);
        }
        .title-block p {
            color: var(--text-muted);
            font-size: 0.95rem;
            margin-top: 4px;
        }
        .header-actions {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }
        .version-label {
            color: var(--text-muted);
            font-size: 0.78rem;
            margin-top: 6px;
            letter-spacing: 0.02em;
        }
        .btn-maj-disponible {
            background-color: var(--accent-green) !important;
            color: #052e16 !important;
            animation: pulse-maj 2s ease-in-out infinite;
        }
        @keyframes pulse-maj {
            0%, 100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.35); }
            50% { box-shadow: 0 0 0 6px rgba(34, 197, 94, 0); }
        }
        .wake-setting {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px 16px;
            margin: -10px 0 22px;
            padding: 10px 14px;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 10px;
        }
        .wake-toggle {
            display: inline-flex;
            align-items: center;
            gap: 9px;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            user-select: none;
        }
        .wake-toggle input[type="checkbox"] {
            width: 17px;
            height: 17px;
            accent-color: var(--primary);
            cursor: pointer;
        }
        .wake-hint {
            color: var(--text-muted);
            font-size: 0.8rem;
        }
        button, .btn {
            background-color: var(--primary);
            color: #0f172a;
            border: none;
            padding: 9px 16px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        button:hover, .btn:hover {
            background-color: var(--primary-hover);
            color: #ffffff;
            transform: translateY(-1px);
        }
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .btn-secondary {
            background-color: var(--card-bg);
            color: var(--text-main);
            border: 1px solid var(--card-border);
        }
        .btn-secondary:hover {
            background-color: var(--card-border);
            color: var(--text-main);
        }
        .grid-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 10px;
            margin-bottom: 18px;
        }
        .camera-card {
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 10px 14px;
            position: relative;
            box-shadow: 0 2px 4px -1px rgba(0, 0, 0, 0.2);
            transition: border-color 0.2s ease;
        }
        .camera-card:hover {
            border-color: var(--primary);
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 4px;
        }
        .camera-name {
            font-size: 1.05rem;
            font-weight: 700;
        }
        .camera-model {
            font-size: 0.68rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .temp-display {
            display: flex;
            align-items: baseline;
            gap: 8px;
            margin: 6px 0;
        }
        .temp-c {
            font-size: 2.2rem;
            font-weight: 800;
            line-height: 1;
            color: #38bdf8;
        }
        .card-badges {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-top: 6px;
        }
        .badge {
            font-size: 0.7rem;
            padding: 2px 8px;
            border-radius: 9999px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .badge-green { background: rgba(34, 197, 94, 0.15); color: var(--accent-green); border: 1px solid rgba(34, 197, 94, 0.3); }
        .badge-orange { background: rgba(245, 158, 11, 0.15); color: var(--accent-orange); border: 1px solid rgba(245, 158, 11, 0.3); }
        .badge-gray { background: rgba(148, 163, 184, 0.15); color: var(--text-muted); border: 1px solid rgba(148, 163, 184, 0.3); }
        
        .card-footer {
            margin-top: 8px;
            padding-top: 6px;
            border-top: 1px solid rgba(255, 255, 255, 0.06);
            font-size: 0.7rem;
            color: var(--text-muted);
            display: flex;
            justify-content: space-between;
        }

        .section-box {
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 32px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        }
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
            flex-wrap: wrap;
            gap: 12px;
        }
        .section-title {
            font-size: 1.25rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .toolbar-group {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .chart-wrapper {
            position: relative;
            width: 100%;
            height: 420px;
            background: #0f172a;
            border-radius: 10px;
            border: 1px solid var(--card-border);
            overflow: hidden;
            margin-top: 14px;
        }
        canvas#chart-canvas {
            width: 100%;
            height: 100%;
            display: block;
            cursor: grab;
        }

        /* Frise chronologique de navigation transversale */
        .timeline-wrapper {
            position: relative;
            width: 100%;
            height: 40px;
            background: #090e1a;
            border-radius: 8px;
            border: 1px solid var(--card-border);
            margin-top: 10px;
            cursor: pointer;
            overflow: hidden;
            user-select: none;
        }
        canvas#timeline-canvas {
            width: 100%;
            height: 100%;
            display: block;
        }

        .chart-info-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 12px;
            font-size: 0.85rem;
            color: var(--text-muted);
        }
        .zoom-status-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(56, 189, 248, 0.1);
            color: var(--primary);
            border: 1px solid rgba(56, 189, 248, 0.25);
            padding: 4px 10px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.82rem;
        }
        .chart-controls-hint {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.82rem;
            color: var(--text-muted);
        }
        .nav-btn {
            background: #0f172a;
            color: var(--text-muted);
            border: 1px solid var(--card-border);
            padding: 5px 11px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .nav-btn:hover {
            color: var(--primary);
            border-color: var(--primary);
            background: rgba(56, 189, 248, 0.1);
        }

        /* Tooltip flottant */
        .chart-tooltip {
            position: absolute;
            pointer-events: none;
            background: rgba(15, 23, 42, 0.95);
            border: 1px solid var(--primary);
            border-radius: 8px;
            padding: 10px 14px;
            color: var(--text-main);
            font-size: 0.85rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.7);
            display: none;
            z-index: 50;
            min-width: 170px;
            backdrop-filter: blur(4px);
        }
        .tooltip-date {
            color: var(--text-muted);
            font-size: 0.78rem;
            margin-bottom: 6px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 4px;
            font-weight: 600;
        }
        .tooltip-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin: 3px 0;
            font-size: 0.85rem;
        }
        .tooltip-camera-name {
            display: flex;
            align-items: center;
            gap: 6px;
            font-weight: 600;
        }
        .tooltip-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }

        /* Légende interactive */
        .chart-legend {
            display: flex;
            gap: 14px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .camera-selector {
            display: flex;
            align-items: center;
            gap: 14px;
            flex-wrap: wrap;
            margin: 4px 0 14px 0;
            padding: 8px 14px;
            background: #0f172a;
            border: 1px solid var(--card-border);
            border-radius: 10px;
        }
        .camera-selector-label {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
        }
        .camera-selector-actions {
            display: flex;
            gap: 6px;
            margin-left: auto;
        }
        .legend-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 0.88rem;
            font-weight: 600;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 6px 14px;
            border-radius: 8px;
            cursor: pointer;
            user-select: none;
            transition: all 0.2s ease;
        }
        .legend-pill:hover {
            border-color: var(--primary);
            transform: translateY(-1px);
        }
        .legend-pill input[type="checkbox"] {
            accent-color: var(--primary);
            cursor: pointer;
        }
        .legend-pill.disabled {
            opacity: 0.45;
        }
        .legend-indicator {
            width: 12px;
            height: 12px;
            border-radius: 3px;
        }

        /* Sélecteur de date manuel */
        .date-picker-group {
            display: flex;
            align-items: center;
            gap: 8px;
            background: #0f172a;
            padding: 4px 10px;
            border-radius: 8px;
            border: 1px solid var(--card-border);
            font-size: 0.82rem;
        }
        .date-picker-group input[type="date"] {
            background: transparent;
            border: none;
            color: var(--text-main);
            font-size: 0.82rem;
            outline: none;
            font-family: inherit;
        }
        .date-picker-group input[type="date"]::-webkit-calendar-picker-indicator {
            filter: invert(1);
            cursor: pointer;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            margin-top: 12px;
        }
        th, td {
            padding: 12px 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }
        th {
            color: var(--text-muted);
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
        }
        td { font-size: 0.95rem; }
        tr:hover td { background: rgba(255, 255, 255, 0.02); }
        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: var(--card-bg);
            border: 1px solid var(--primary);
            color: var(--text-main);
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
            display: none;
            z-index: 100;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="title-block">
                <h1>🌡️ Blink2Temp</h1>
                <p>Surveillance, graphiques interactifs et historique horaire des températures extérieures</p>
                <p id="version-app" class="version-label"></p>
            </div>
            <div class="header-actions">
                <button id="btn-maj" class="btn btn-secondary" onclick="actionMaj()" title="Installer la dernière version depuis GitHub">
                    ⬆️ Vérifier la mise à jour
                </button>
                <button id="btn-refresh" onclick="declencherReleve()">
                    🔄 Relever maintenant
                </button>
                <a href="/api/export.csv" class="btn btn-secondary" download="temperatures_outdoor.csv">
                    📥 Exporter CSV
                </a>
            </div>
        </header>

        <!-- Option de réveil des caméras (consomme la pile) -->
        <div class="wake-setting">
            <label class="wake-toggle" title="Une commande photo force la caméra à renvoyer sa température à jour.">
                <input type="checkbox" id="input-reveil-cameras" onchange="basculerReveilCameras(this.checked)">
                <span>🔋 Réveiller les caméras si la température n'a pas changé</span>
            </label>
            <span class="wake-hint">
                Une photo consomme la pile et peut durer une minute par caméra.
                En relève planifiée : au plus une fois par heure. Une relève manuelle force le réveil.
            </span>
        </div>

        <!-- Cartes en direct par caméra -->
        <div id="cards-container" class="grid-cards">
            <!-- Rempli par JavaScript -->
        </div>

        <!-- Section Graphique Interactif avec Zoom Molette & Déplacement Transversal -->
        <div class="section-box">
            <div class="section-header">
                <div class="section-title">
                    📈 Courbes des Températures
                </div>
                <div class="toolbar-group">
                    <div class="date-picker-group">
                        <span>Du</span>
                        <input type="date" id="input-date-debut" onchange="appliquerPlageDate()">
                        <span>Au</span>
                        <input type="date" id="input-date-fin" onchange="appliquerPlageDate()">
                    </div>
                    <button class="btn btn-secondary" style="padding:6px 12px; font-size:0.82rem;" onclick="reinitialiserZoom()">
                        ↺ Réinitialiser vue
                    </button>
                </div>
            </div>

            <!-- Sélecteur de caméras à afficher -->
            <div class="camera-selector">
                <div class="camera-selector-label">Caméras affichées :</div>
                <div class="chart-legend" id="chart-legend">
                    <!-- Rempli par JS -->
                </div>
                <div class="camera-selector-actions">
                    <button class="nav-btn" onclick="toutesCameras(true)" title="Afficher toutes les caméras">Toutes</button>
                    <button class="nav-btn" onclick="toutesCameras(false)" title="Masquer toutes les caméras">Aucune</button>
                </div>
            </div>

            <!-- Conteneur Canvas Principal -->
            <div class="chart-wrapper" id="chart-wrapper">
                <canvas id="chart-canvas"></canvas>
                <div id="chart-tooltip" class="chart-tooltip"></div>
            </div>

            <!-- Frise chronologique / Mini-carte transversale interactive -->
            <div class="timeline-wrapper" id="timeline-wrapper" title="Frise chronologique : glissez pour vous déplacer transversalement sur l'axe des dates">
                <canvas id="timeline-canvas"></canvas>
            </div>

            <div class="chart-info-bar">
                <span id="zoom-status" class="zoom-status-pill">
                    🔎 Zoom initial
                </span>
                <div style="display:flex; align-items:center; gap:6px;">
                    <button class="nav-btn" onclick="deplacerTempsTransversal(-0.25)" title="Déplacer l'axe des dates vers la gauche (reculer)">◀ Reculer</button>
                    <button class="nav-btn" onclick="deplacerTempsTransversal(0.25)" title="Déplacer l'axe des dates vers la droite (avancer)">Avancer ▶</button>
                </div>
                <span class="chart-controls-hint">
                    ↔️ <strong>Glisser souris</strong> ou <strong>Shift + Molette</strong> : Déplacement transversal | <strong>Molette</strong> : Zoom | <strong>Double-clic</strong> : Vue complète
                </span>
            </div>
        </div>

        <!-- Tableau des Statistiques -->
        <div class="section-box">
            <div class="section-header">
                <div class="section-title">📊 Synthèse Statistique (Période affichée)</div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Caméra</th>
                        <th>Modèle</th>
                        <th>Min (${UNITE_TEMP})</th>
                        <th>Moyenne (${UNITE_TEMP})</th>
                        <th>Max (${UNITE_TEMP})</th>
                        <th>Mesures</th>
                    </tr>
                </thead>
                <tbody id="stats-table">
                    <!-- Rempli par JS -->
                </tbody>
            </table>
        </div>
    </div>

    <div id="toast" class="toast"></div>

    <script>
        const PALETTE = [
            "#38bdf8", // Sky Blue
            "#22c55e", // Green
            "#f59e0b", // Amber
            "#ec4899", // Pink
            "#a855f7", // Purple
            "#14b8a6", // Teal
            "#f97316"  // Orange
        ];

        // ==========================================
        // UNITÉ DE TEMPÉRATURE SELON LA LANGUE DU NAVIGATEUR
        // ==========================================
        const TERRITOIRES_FAHRENHEIT = new Set([
            "AS", "BQ", "BS", "FM", "GU", "IO", "JM", "KY", "LR", "MH", "MM",
            "MP", "PW", "PR", "PS", "SX", "TC", "TL", "UM", "US", "VG", "VI"
        ]);
        const REGION_NAVIGATEUR = (function () {
            const langue = navigator.language || "fr";
            try {
                return (new Intl.Locale(langue).region || langue.split("-")[1] || "").toUpperCase();
            } catch (e) {
                return (langue.split("-")[1] || "").toUpperCase();
            }
        })();
        const UTILISE_FAHRENHEIT = TERRITOIRES_FAHRENHEIT.has(REGION_NAVIGATEUR);
        const UNITE_TEMP = UTILISE_FAHRENHEIT ? "°F" : "°C";
        // Convertit une température °C vers l'unité du navigateur (null conservé)
        function versUnite(tempC) {
            if (tempC === null || tempC === undefined) return null;
            return UTILISE_FAHRENHEIT ? tempC * 9 / 5 + 32 : tempC;
        }

        let donneesBrutes = [];
        let seriesParCamera = {};
        let cameraVisibilite = {};
        let cameraCouleurs = {};
        // Préférence de visibilité persistée côté serveur (config.json)
        let cameraVisibiliteServeur = {};
        // Option de réveil des caméras persistée côté serveur (config.json)
        let reveilCameras = false;

        async function chargerReglages() {
            try {
                const res = await fetch("/api/reglages");
                const r = await res.json();
                reveilCameras = Boolean(r.reveiller_cameras);
                const input = document.getElementById("input-reveil-cameras");
                if (input) input.checked = reveilCameras;
            } catch (err) {
                console.error("Erreur de chargement des réglages:", err);
            }
        }

        async function basculerReveilCameras(actif) {
            const precedent = reveilCameras;
            reveilCameras = Boolean(actif);
            try {
                const res = await fetch("/api/reglages", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ reveiller_cameras: reveilCameras })
                });
                const r = await res.json();
                if (!r.ok) throw new Error(r.error || "Enregistrement refusé");
                afficherToast(reveilCameras
                    ? "🔋 Réveil activé : les caméras seront sollicitées si leur température ne change pas."
                    : "🔋 Réveil désactivé.");
            } catch (err) {
                reveilCameras = precedent;
                const input = document.getElementById("input-reveil-cameras");
                if (input) input.checked = precedent;
                afficherToast("⚠️ Impossible d'enregistrer l'option : " + err);
            }
        }

        // Fenêtre temporelle d'affichage (en millisecondes)
        let tempsMinVue = 0;
        let tempsMaxVue = 0;
        let tempsMinTotal = 0;
        let tempsMaxTotal = 0;

        // Plage de données demandée au serveur ("all" = tout l'historique).
        // Elle est réutilisée lors des rafraîchissements automatiques pour ne pas
        // écraser un filtre de dates ni le zoom en cours.
        let plageCourante = { heures: "all", debut: null, fin: null };
        let vueInitialisee = false;

        // Interaction souris sur le graphique principal
        let isDraggingMain = false;
        let isDraggingAxis = false;
        let dragStartX = 0;
        let dragStartMin = 0;
        let dragStartMax = 0;
        let hoverPixelX = null;
        let hoverPixelY = null;

        // Interaction souris sur la frise chronologique (timeline minimap)
        let isDraggingTimeline = false;
        let timelineDragStartX = 0;
        let timelineDragStartMin = 0;
        let timelineDragStartMax = 0;

        const canvas = document.getElementById("chart-canvas");
        const ctx = canvas.getContext("2d");
        const timelineCanvas = document.getElementById("timeline-canvas");
        const timelineCtx = timelineCanvas.getContext("2d");
        const tooltip = document.getElementById("chart-tooltip");
        const chartWrapper = document.getElementById("chart-wrapper");
        const timelineWrapper = document.getElementById("timeline-wrapper");

        // Marges intérieures du graphique principal
        const padLeft = 55;
        const padRight = 30;
        const padTop = 25;
        const padBottom = 38;

        function afficherToast(message) {
            const t = document.getElementById("toast");
            t.textContent = message;
            t.style.display = "block";
            setTimeout(() => { t.style.display = "none"; }, 3500);
        }

        // ==========================================================
        // MISE À JOUR DEPUIS LA DERNIÈRE RELEASE GITHUB
        // ==========================================================

        let majDisponible = null;
        let majSuivi = null;
        let majRedemarrageSuivi = false;

        async function recupererEtatMaj(force = false) {
            const res = await fetch(`/api/maj${force ? "?force=1" : ""}`, { cache: "no-store" });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return res.json();
        }

        function appliquerEtatMaj(etat) {
            majDisponible = etat.disponible || null;
            const btn = document.getElementById("btn-maj");
            const version = document.getElementById("version-app");
            if (version) version.textContent = `Version ${etat.version_locale || "?"}`;
            if (!btn) return;

            btn.classList.remove("btn-maj-disponible");
            const phase = etat.etape || "inactif";

            if (phase === "verification") {
                btn.disabled = true;
                btn.textContent = "⏳ Recherche…";
                return;
            }
            if (phase === "telechargement" || phase === "extraction" || phase === "installation") {
                btn.disabled = true;
                if (phase === "telechargement") {
                    btn.textContent = `⬇️ Téléchargement ${Math.round((etat.progression || 0) * 100)} %`;
                } else if (phase === "extraction") {
                    btn.textContent = "📦 Vérification de l'archive…";
                } else {
                    btn.textContent = "⚙️ Installation…";
                }
                return;
            }
            if (phase === "redemarrage") {
                btn.disabled = true;
                btn.textContent = "♻️ Redémarrage…";
                surveillerRedemarrage();
                return;
            }

            btn.disabled = false;
            if (majDisponible) {
                btn.textContent = `⬆️ Mettre à jour ${majDisponible.version}`;
                btn.classList.add("btn-maj-disponible");
                btn.title = `Installer Blink2Temp ${majDisponible.version} depuis GitHub`;
            } else {
                btn.textContent = "⬆️ Vérifier la mise à jour";
                btn.title = "Installer la dernière version depuis GitHub";
            }
            if (phase === "erreur" && etat.erreur) {
                afficherToast("⚠️ Mise à jour : " + etat.erreur);
            }
        }

        function suivreMaj() {
            if (majSuivi) return;
            majSuivi = setInterval(async () => {
                try {
                    const etat = await recupererEtatMaj();
                    appliquerEtatMaj(etat);
                    if (!["verification", "telechargement", "extraction", "installation", "redemarrage"].includes(etat.etape)) {
                        clearInterval(majSuivi);
                        majSuivi = null;
                    }
                } catch (_) {
                    // Le serveur s'arrête pour redémarrer : la boucle continue.
                }
            }, 1000);
        }

        async function chargerEtatMaj(force = false) {
            try {
                const etat = await recupererEtatMaj(force);
                appliquerEtatMaj(etat);
                if (etat.etape === "verification") suivreMaj();
            } catch (_) {
                // Vérification non bloquante : le reste du tableau de bord continue.
            }
        }

        async function actionMaj() {
            const btn = document.getElementById("btn-maj");
            if (!majDisponible) {
                btn.disabled = true;
                try {
                    const etat = await recupererEtatMaj(true);
                    appliquerEtatMaj(etat);
                    suivreMaj();
                    for (let i = 0; i < 40; i++) {
                        await new Promise(r => setTimeout(r, 500));
                        const courant = await recupererEtatMaj();
                        appliquerEtatMaj(courant);
                        if (courant.etape !== "verification") break;
                    }
                } catch (err) {
                    afficherToast("⚠️ Vérification impossible : " + err);
                    btn.disabled = false;
                    return;
                }
            }

            if (!majDisponible) {
                afficherToast("✅ Blink2Temp est à jour.");
                return;
            }
            if (!confirm(`Installer Blink2Temp ${majDisponible.version} ?\n\nL'application va s'arrêter puis redémarrer.`)) {
                return;
            }

            btn.disabled = true;
            btn.textContent = "⬇️ Préparation…";
            try {
                const res = await fetch("/api/maj", { method: "POST" });
                const etat = await res.json();
                if (!res.ok) {
                    appliquerEtatMaj(await recupererEtatMaj());
                    afficherToast("⚠️ " + (etat.erreur || "Mise à jour refusée."));
                    return;
                }
                appliquerEtatMaj(etat);
                suivreMaj();
            } catch (err) {
                afficherToast("⚠️ Impossible de lancer la mise à jour : " + err);
                btn.disabled = false;
            }
        }

        async function surveillerRedemarrage() {
            if (majRedemarrageSuivi) return;
            majRedemarrageSuivi = true;
            for (let i = 0; i < 120; i++) {
                await new Promise(r => setTimeout(r, 1000));
                try {
                    const res = await fetch("/api/maj", { cache: "no-store" });
                    if (res.ok) {
                        location.reload();
                        return;
                    }
                } catch (_) {
                    // Encore en redémarrage.
                }
            }
            afficherToast("⚠️ Le redémarrage prend trop de temps. Relancez Blink2Temp.");
        }

        async function chargerDonneesInitiales() {
            try {
                const [resLatest, resVisibilite] = await Promise.all([
                    fetch("/api/latest"),
                    fetch("/api/visibilite")
                ]);
                const cartes = await resLatest.json();
                cameraVisibiliteServeur = await resVisibilite.json() || {};
                afficherCartes(cartes);

                // À l'ouverture : tout l'historique, avec la courbe entière visible.
                // Ensuite : on conserve le zoom et le filtre de dates en cours.
                await chargerHistorique(
                    plageCourante.heures,
                    plageCourante.debut,
                    plageCourante.fin,
                    !vueInitialisee
                );
            } catch (err) {
                console.error("Erreur de chargement initial:", err);
            }
        }

        function afficherCartes(cameras) {
            const container = document.getElementById("cards-container");
            // Seules les caméras qui remontent une température sont affichées,
            // comme sur Android.
            cameras = (cameras || []).filter(
                (c) => c.temp_c !== null && c.temp_c !== undefined
            );
            if (cameras.length === 0) {
                container.innerHTML = "<p style='color:var(--text-muted);'>Aucune caméra ne remonte de température pour le moment.</p>";
                return;
            }
            container.innerHTML = cameras.map((c) => {
                const tempC = c.temp_c;
                const tempAffichee = tempC !== null ? versUnite(tempC).toFixed(1) + UNITE_TEMP : "--";
                const isOnline = c.status !== "offline";
                const statusBadge = isOnline ? 
                    '<span class="badge badge-green">● En ligne</span>' : 
                    '<span class="badge badge-gray">● Hors ligne</span>';
                
                let batteryBadge = '<span class="badge badge-green">🔋 Pile OK</span>';
                if (c.battery === "low") {
                    batteryBadge = '<span class="badge badge-orange">🪫 Pile faible</span>';
                }

                return `
                    <div class="camera-card">
                        <div class="card-header">
                            <div>
                                <div class="camera-name">${c.camera_name}</div>
                                <div class="camera-model">${c.model || "Blink Outdoor"}</div>
                            </div>
                            <span class="badge badge-gray">Outdoor</span>
                        </div>
                        <div class="temp-display">
                            <span class="temp-c">${tempAffichee}</span>
                        </div>
                        <div class="card-badges">
                            ${statusBadge}
                            ${batteryBadge}
                            ${c.wifi_strength ? `<span class="badge badge-gray">📶 Wi-Fi ${c.wifi_strength}</span>` : ""}
                        </div>
                        <div class="card-footer">
                            <span>Dernier relevé : ${c.local_time.split(" ")[1]}</span>
                            <span>Date : ${c.local_time.split(" ")[0]}</span>
                        </div>
                    </div>
                `;
            }).join("");
        }

        async function chargerHistorique(heures, debut = null, fin = null, ajusterVue = true) {
            plageCourante = { heures, debut, fin };

            let url = "/api/history?";
            if (debut && fin) {
                url += `start=${encodeURIComponent(debut)}&end=${encodeURIComponent(fin)}`;
            } else {
                url += `hours=${heures}`;
            }

            try {
                const res = await fetch(url);
                donneesBrutes = await res.json();
                traiterDonnees();
                if (ajusterVue) {
                    reinitialiserZoom();
                } else {
                    recalculerBornesTotales();
                    mettreAJourZoomUI();
                    dessinerGraphique();
                    dessinerFriseChronologique();
                }
                mettreAJourStats();
                vueInitialisee = true;
            } catch (err) {
                console.error("Échec du chargement de l'historique:", err);
            }
        }

        function traiterDonnees() {
            seriesParCamera = {};
            const noms = new Set();

            donneesBrutes.forEach(d => {
                if (d.temp_c === null) return;
                const nom = d.camera_name;
                noms.add(nom);
                if (!seriesParCamera[nom]) {
                    seriesParCamera[nom] = [];
                }
                const timeMs = new Date(d.recorded_at).getTime();
                seriesParCamera[nom].push({
                    time: timeMs,
                    temp: versUnite(d.temp_c),
                    localTime: d.local_time,
                });
            });

            // Tri par date
            Object.values(seriesParCamera).forEach(arr => arr.sort((a, b) => a.time - b.time));

            // Couleurs et visibilités
            Array.from(noms).forEach((nom, index) => {
                if (!cameraCouleurs[nom]) {
                    cameraCouleurs[nom] = PALETTE[index % PALETTE.length];
                }
                if (cameraVisibilite[nom] === undefined) {
                    cameraVisibilite[nom] = cameraVisibiliteServeur[nom] !== undefined
                        ? Boolean(cameraVisibiliteServeur[nom])
                        : true;
                }
            });

            genererLegende();
        }

        function genererLegende() {
            const legendBox = document.getElementById("chart-legend");
            const noms = Object.keys(seriesParCamera);
            if (noms.length === 0) {
                legendBox.innerHTML = "";
                return;
            }

            legendBox.innerHTML = noms.map(nom => {
                const couleur = cameraCouleurs[nom];
                const active = cameraVisibilite[nom];
                return `
                    <label class="legend-pill ${active ? '' : 'disabled'}" title="Cocher/décocher pour afficher ou masquer la courbe">
                        <input type="checkbox" ${active ? 'checked' : ''} onclick="basculerCamera('${nom}')">
                        <div class="legend-indicator" style="background:${couleur};"></div>
                        <span>${nom}</span>
                    </label>
                `;
            }).join("");
        }

        async function sauvegarderVisibilite() {
            try {
                await fetch("/api/visibilite", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(cameraVisibilite),
                });
            } catch (err) {
                console.error("Échec de la sauvegarde de la visibilité des caméras:", err);
            }
        }

        function basculerCamera(nom) {
            cameraVisibilite[nom] = !cameraVisibilite[nom];
            genererLegende();
            mettreAJourStats();
            dessinerGraphique();
            dessinerFriseChronologique();
            sauvegarderVisibilite();
        }

        function toutesCameras(visible) {
            Object.keys(cameraVisibilite).forEach(nom => {
                cameraVisibilite[nom] = visible;
            });
            genererLegende();
            mettreAJourStats();
            reinitialiserZoom();
            sauvegarderVisibilite();
        }

        function recalculerBornesTotales() {
            const tousTemps = [];
            Object.keys(seriesParCamera).forEach(nom => {
                if (!cameraVisibilite[nom]) return;
                seriesParCamera[nom].forEach(p => tousTemps.push(p.time));
            });

            if (tousTemps.length === 0) {
                tempsMinTotal = Date.now() - 24 * 3600 * 1000;
                tempsMaxTotal = Date.now();
            } else {
                tempsMinTotal = Math.min(...tousTemps);
                tempsMaxTotal = Math.max(...tousTemps);
                if (tempsMinTotal === tempsMaxTotal) {
                    tempsMinTotal -= 1800 * 1000;
                    tempsMaxTotal += 1800 * 1000;
                }
            }
        }

        function reinitialiserZoom() {
            recalculerBornesTotales();

            tempsMinVue = tempsMinTotal;
            tempsMaxVue = tempsMaxTotal;

            mettreAJourZoomUI();
            dessinerGraphique();
            dessinerFriseChronologique();
        }

        function deplacerTempsTransversal(fraction) {
            const span = tempsMaxVue - tempsMinVue;
            const shiftMs = span * fraction;
            tempsMinVue += shiftMs;
            tempsMaxVue += shiftMs;

            mettreAJourZoomUI();
            dessinerGraphique();
            dessinerFriseChronologique();
        }

        function mettreAJourZoomUI() {
            const el = document.getElementById("zoom-status");
            const d1 = new Date(tempsMinVue);
            const d2 = new Date(tempsMaxVue);

            const opt = { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" };
            const str1 = d1.toLocaleString("fr-FR", opt);
            const str2 = d2.toLocaleString("fr-FR", opt);

            const spanHours = (tempsMaxVue - tempsMinVue) / (3600 * 1000);
            let spanTxt = `${spanHours.toFixed(1)}h`;
            if (spanHours >= 48) {
                spanTxt = `${(spanHours / 24).toFixed(1)} jours`;
            }

            el.innerHTML = `📅 Axe des dates : <strong>${str1}</strong> ➔ <strong>${str2}</strong> (${spanTxt})`;
        }

        function redimensionnerCanvas() {
            const dpr = window.devicePixelRatio || 1;

            // Canvas principal
            const rect = chartWrapper.getBoundingClientRect();
            canvas.width = rect.width * dpr;
            canvas.height = rect.height * dpr;
            ctx.resetTransform();
            ctx.scale(dpr, dpr);

            // Canvas frise chronologique
            const tRect = timelineWrapper.getBoundingClientRect();
            timelineCanvas.width = tRect.width * dpr;
            timelineCanvas.height = tRect.height * dpr;
            timelineCtx.resetTransform();
            timelineCtx.scale(dpr, dpr);

            dessinerGraphique();
            dessinerFriseChronologique();
        }

        function formaterAxeTemps(valeurDate, spanMs) {
            const d = new Date(valeurDate);
            if (spanMs > 7 * 24 * 3600 * 1000) {
                return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" });
            }
            if (spanMs > 36 * 3600 * 1000) {
                return `${d.getDate()}/${d.getMonth()+1} ${String(d.getHours()).padStart(2, '0')}h`;
            }
            if (spanMs > 10 * 60 * 1000) {
                return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
            }
            return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`;
        }

        // ==========================================
        // RENDU DU GRAPHIQUE PRINCIPAL
        // ==========================================

        function dessinerGraphique() {
            const rect = chartWrapper.getBoundingClientRect();
            const width = rect.width;
            const height = rect.height;

            ctx.clearRect(0, 0, width, height);

            const plotW = width - padLeft - padRight;
            const plotH = height - padTop - padBottom;
            const spanT = Math.max(1, tempsMaxVue - tempsMinVue);

            // Trouver min/max température dans la fenêtre de zoom
            let minTemp = Infinity;
            let maxTemp = -Infinity;
            let aDesDonnees = false;

            Object.keys(seriesParCamera).forEach(nom => {
                if (!cameraVisibilite[nom]) return;
                seriesParCamera[nom].forEach(p => {
                    if (p.time >= tempsMinVue && p.time <= tempsMaxVue) {
                        aDesDonnees = true;
                        if (p.temp < minTemp) minTemp = p.temp;
                        if (p.temp > maxTemp) maxTemp = p.temp;
                    }
                });
            });

            if (!aDesDonnees) {
                minTemp = 0;
                maxTemp = 30;
            } else {
                minTemp = Math.floor(minTemp - 1.5);
                maxTemp = Math.ceil(maxTemp + 1.5);
                if (minTemp === maxTemp) {
                    minTemp -= 5;
                    maxTemp += 5;
                }
            }

            const spanTemp = maxTemp - minTemp;

            // 1. Grille horizontale & Axe Y (Températures)
            ctx.font = "11px " + getComputedStyle(document.body).fontFamily;
            ctx.fillStyle = "#94a3b8";
            ctx.textAlign = "right";
            ctx.textBaseline = "middle";

            const nbLignesY = 6;
            const pasY = spanTemp / nbLignesY;
            for (let i = 0; i <= nbLignesY; i++) {
                const tempVal = minTemp + i * pasY;
                const y = padTop + plotH - ((tempVal - minTemp) / spanTemp) * plotH;

                ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
                ctx.setLineDash([4, 4]);
                ctx.beginPath();
                ctx.moveTo(padLeft, y);
                ctx.lineTo(width - padRight, y);
                ctx.stroke();

                ctx.fillText(tempVal.toFixed(1) + UNITE_TEMP, padLeft - 10, y);
            }

            // Bandeau de l'axe des dates (mise en valeur pour déplacement transversal)
            ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
            ctx.fillRect(padLeft, height - padBottom, plotW, padBottom);
            ctx.strokeStyle = "rgba(255, 255, 255, 0.12)";
            ctx.setLineDash([]);
            ctx.beginPath();
            ctx.moveTo(padLeft, height - padBottom);
            ctx.lineTo(width - padRight, height - padBottom);
            ctx.stroke();

            // 2. Grille verticale & Axe X (Dates & Heures)
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            const nbLignesX = Math.max(3, Math.min(8, Math.floor(plotW / 120)));
            for (let i = 0; i <= nbLignesX; i++) {
                const timeVal = tempsMinVue + (i / nbLignesX) * spanT;
                const x = padLeft + (i / nbLignesX) * plotW;

                ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
                ctx.setLineDash([4, 4]);
                ctx.beginPath();
                ctx.moveTo(x, padTop);
                ctx.lineTo(x, height - padBottom);
                ctx.stroke();

                // Graduations sur l'axe des dates
                ctx.strokeStyle = "rgba(255, 255, 255, 0.3)";
                ctx.setLineDash([]);
                ctx.beginPath();
                ctx.moveTo(x, height - padBottom);
                ctx.lineTo(x, height - padBottom + 5);
                ctx.stroke();

                const libelleTemps = formaterAxeTemps(timeVal, spanT);
                ctx.fillStyle = "#cbd5e1";
                ctx.fillText(libelleTemps, x, height - padBottom + 9);
            }

            if (!aDesDonnees) {
                ctx.fillStyle = "#94a3b8";
                ctx.font = "14px " + getComputedStyle(document.body).fontFamily;
                ctx.textAlign = "center";
                ctx.fillText("Aucune donnée enregistrée dans cette plage de dates.", width / 2, height / 2);
                return;
            }

            // 3. Tracé des courbes de chaque caméra
            const pointsSousCurseur = [];

            Object.keys(seriesParCamera).forEach(nom => {
                if (!cameraVisibilite[nom]) return;
                const pts = seriesParCamera[nom];
                const couleur = cameraCouleurs[nom];

                const pointsVisibles = pts.map(p => {
                    const x = padLeft + ((p.time - tempsMinVue) / spanT) * plotW;
                    const y = padTop + plotH - ((p.temp - minTemp) / spanTemp) * plotH;
                    return { x, y, data: p, nom };
                });

                if (pointsVisibles.length === 0) return;

                // Ligne
                ctx.beginPath();
                ctx.strokeStyle = couleur;
                ctx.lineWidth = 2.5;
                ctx.lineJoin = "round";
                ctx.lineCap = "round";

                let started = false;
                pointsVisibles.forEach(pt => {
                    if (!started) {
                        ctx.moveTo(pt.x, pt.y);
                        started = true;
                    } else {
                        ctx.lineTo(pt.x, pt.y);
                    }
                });
                ctx.stroke();

                // Points individuels
                pointsVisibles.forEach(pt => {
                    if (pt.x >= padLeft - 10 && pt.x <= width - padRight + 10) {
                        ctx.beginPath();
                        ctx.arc(pt.x, pt.y, 4, 0, Math.PI * 2);
                        ctx.fillStyle = couleur;
                        ctx.fill();
                        ctx.strokeStyle = "#0f172a";
                        ctx.lineWidth = 1.5;
                        ctx.stroke();
                    }
                });

                // Trouver le point le plus proche du survol souris
                if (hoverPixelX !== null) {
                    let pointPlusProche = null;
                    let distanceMin = 40;

                    pointsVisibles.forEach(pt => {
                        const dist = Math.abs(pt.x - hoverPixelX);
                        if (dist < distanceMin) {
                            distanceMin = dist;
                            pointPlusProche = pt;
                        }
                    });

                    if (pointPlusProche) {
                        pointsSousCurseur.push(pointPlusProche);
                    }
                }
            });

            // 4. Ligne guide verticale de survol
            if (hoverPixelX !== null && hoverPixelX >= padLeft && hoverPixelX <= width - padRight) {
                ctx.strokeStyle = "rgba(56, 189, 248, 0.4)";
                ctx.lineWidth = 1.5;
                ctx.setLineDash([2, 2]);
                ctx.beginPath();
                ctx.moveTo(hoverPixelX, padTop);
                ctx.lineTo(hoverPixelX, height - padBottom);
                ctx.stroke();
                ctx.setLineDash([]);

                pointsSousCurseur.forEach(pt => {
                    ctx.beginPath();
                    ctx.arc(pt.x, pt.y, 7, 0, Math.PI * 2);
                    ctx.fillStyle = "#ffffff";
                    ctx.fill();
                    ctx.strokeStyle = cameraCouleurs[pt.nom];
                    ctx.lineWidth = 3;
                    ctx.stroke();
                });
            }
        }

        // ========================================================
        // RENDU DE LA FRISE CHRONOLOGIQUE TRANSVERSALE (MINIMAP)
        // ========================================================

        function dessinerFriseChronologique() {
            const rect = timelineWrapper.getBoundingClientRect();
            const width = rect.width;
            const height = rect.height;

            timelineCtx.clearRect(0, 0, width, height);

            const spanTotal = Math.max(1, tempsMaxTotal - tempsMinTotal);

            // Tracé miniature d'arrière-plan des points
            Object.keys(seriesParCamera).forEach(nom => {
                if (!cameraVisibilite[nom]) return;
                const pts = seriesParCamera[nom];
                const couleur = cameraCouleurs[nom];

                timelineCtx.fillStyle = couleur;
                pts.forEach(p => {
                    const x = ((p.time - tempsMinTotal) / spanTotal) * width;
                    timelineCtx.fillRect(x - 1, 12, 2, height - 16);
                });
            });

            // Rectangle représentant la fenêtre temporelle visible courante
            const x1 = Math.max(0, Math.min(width, ((tempsMinVue - tempsMinTotal) / spanTotal) * width));
            const x2 = Math.max(0, Math.min(width, ((tempsMaxVue - tempsMinTotal) / spanTotal) * width));
            const wVue = Math.max(12, x2 - x1);

            // Cadre translucide
            timelineCtx.fillStyle = "rgba(56, 189, 248, 0.22)";
            timelineCtx.fillRect(x1, 2, wVue, height - 4);
            timelineCtx.strokeStyle = "rgba(56, 189, 248, 0.85)";
            timelineCtx.lineWidth = 2;
            timelineCtx.strokeRect(x1, 2, wVue, height - 4);

            // Poignées de redimensionnement aux extrémités
            timelineCtx.fillStyle = "#38bdf8";
            timelineCtx.fillRect(x1 - 2, 8, 4, height - 16);
            timelineCtx.fillRect(x1 + wVue - 2, 8, 4, height - 16);

            // Texte de repère
            timelineCtx.font = "10px " + getComputedStyle(document.body).fontFamily;
            timelineCtx.fillStyle = "#94a3b8";
            timelineCtx.textAlign = "left";
            timelineCtx.fillText(new Date(tempsMinTotal).toLocaleDateString("fr-FR"), 6, 10);
            timelineCtx.textAlign = "right";
            timelineCtx.fillText(new Date(tempsMaxTotal).toLocaleDateString("fr-FR"), width - 6, 10);
        }

        // ==========================================================
        // GESTION DU DÉPLACEMENT TRANSVERSAL ET DU ZOOM SOURIS
        // ==========================================================

        // 1. ZOOM ET DÉPLACEMENT TRANSVERSAL À LA MOLETTE
        chartWrapper.addEventListener("wheel", (e) => {
            e.preventDefault();
            const rect = chartWrapper.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const plotW = rect.width - padLeft - padRight;
            if (mouseX < padLeft || mouseX > rect.width - padRight) return;

            // Déplacement transversal direct si Shift est maintenu ou molette horizontale (deltaX)
            if (e.shiftKey || Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
                const delta = e.shiftKey ? (e.deltaY || e.deltaX) : e.deltaX;
                const spanCourant = tempsMaxVue - tempsMinVue;
                const shiftMs = (delta / plotW) * spanCourant * 0.45;
                tempsMinVue += shiftMs;
                tempsMaxVue += shiftMs;

                mettreAJourZoomUI();
                dessinerGraphique();
                dessinerFriseChronologique();
                return;
            }

            // Zoom centré sur la position X du curseur
            const ratioCurseur = (mouseX - padLeft) / plotW;
            const spanCourant = tempsMaxVue - tempsMinVue;
            const tempsCurseur = tempsMinVue + ratioCurseur * spanCourant;

            const facteur = e.deltaY < 0 ? 0.8 : 1.25;
            let nouveauSpan = spanCourant * facteur;

            const minSpan = 3 * 60 * 1000;
            const maxSpan = 10 * 365 * 24 * 3600 * 1000;
            if (nouveauSpan < minSpan) nouveauSpan = minSpan;
            if (nouveauSpan > maxSpan) nouveauSpan = maxSpan;

            tempsMinVue = tempsCurseur - ratioCurseur * nouveauSpan;
            tempsMaxVue = tempsMinVue + nouveauSpan;

            mettreAJourZoomUI();
            dessinerGraphique();
            dessinerFriseChronologique();
            mettreAJourTooltip(e.clientX, e.clientY);
        }, { passive: false });

        // 2. DÉPLACEMENT PAR GLISSER DE SOURIS (GRAPHIQUE PRINCIPAL & AXE DES DATES)
        chartWrapper.addEventListener("mousedown", (e) => {
            if (e.button !== 0) return; // Clic gauche
            const rect = chartWrapper.getBoundingClientRect();
            const mouseY = e.clientY - rect.top;

            isDraggingMain = true;
            isDraggingAxis = (mouseY >= rect.height - padBottom);
            dragStartX = e.clientX;
            dragStartMin = tempsMinVue;
            dragStartMax = tempsMaxVue;

            chartWrapper.style.cursor = isDraggingAxis ? "ew-resize" : "grabbing";
        });

        window.addEventListener("mousemove", (e) => {
            const rect = chartWrapper.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            if (isDraggingMain) {
                // Déplacement transversal en cours
                const plotW = rect.width - padLeft - padRight;
                const deltaPx = e.clientX - dragStartX;
                const deltaMs = (deltaPx / plotW) * (dragStartMax - dragStartMin);

                tempsMinVue = dragStartMin - deltaMs;
                tempsMaxVue = dragStartMax - deltaMs;

                mettreAJourZoomUI();
                dessinerGraphique();
                dessinerFriseChronologique();
            } else {
                // Survol souris
                const estSurAxeDates = (mouseY >= rect.height - padBottom && mouseY <= rect.height);
                chartWrapper.style.cursor = estSurAxeDates ? "ew-resize" : "grab";

                if (mouseX >= padLeft && mouseX <= rect.width - padRight &&
                    mouseY >= padTop && mouseY <= rect.height) {
                    hoverPixelX = mouseX;
                    hoverPixelY = mouseY;
                    mettreAJourTooltip(e.clientX, e.clientY);
                } else {
                    hoverPixelX = null;
                    hoverPixelY = null;
                    tooltip.style.display = "none";
                }
                dessinerGraphique();
            }
        });

        window.addEventListener("mouseup", () => {
            if (isDraggingMain) {
                isDraggingMain = false;
                isDraggingAxis = false;
                chartWrapper.style.cursor = "grab";
            }
            if (isDraggingTimeline) {
                isDraggingTimeline = false;
            }
        });

        chartWrapper.addEventListener("mouseleave", () => {
            if (!isDraggingMain) {
                hoverPixelX = null;
                hoverPixelY = null;
                tooltip.style.display = "none";
                dessinerGraphique();
            }
        });

        chartWrapper.addEventListener("dblclick", () => {
            reinitialiserZoom();
        });

        // 3. GLISSER DIRECT SUR LA FRISE CHRONOLOGIQUE INFÉRIEURE
        timelineWrapper.addEventListener("mousedown", (e) => {
            if (e.button !== 0) return;
            const rect = timelineWrapper.getBoundingClientRect();
            const width = rect.width;
            const mouseX = e.clientX - rect.left;

            isDraggingTimeline = true;
            timelineDragStartX = e.clientX;
            timelineDragStartMin = tempsMinVue;
            timelineDragStartMax = tempsMaxVue;

            // Centrer immédiatement la vue sur le clic
            const spanTotal = Math.max(1, tempsMaxTotal - tempsMinTotal);
            const tempsClic = tempsMinTotal + (mouseX / width) * spanTotal;
            const spanVue = tempsMaxVue - tempsMinVue;

            tempsMinVue = tempsClic - spanVue / 2;
            tempsMaxVue = tempsMinVue + spanVue;

            mettreAJourZoomUI();
            dessinerGraphique();
            dessinerFriseChronologique();
        });

        window.addEventListener("mousemove", (e) => {
            if (isDraggingTimeline) {
                const rect = timelineWrapper.getBoundingClientRect();
                const width = rect.width;
                const deltaPx = e.clientX - timelineDragStartX;
                const spanTotal = Math.max(1, tempsMaxTotal - tempsMinTotal);
                const deltaMs = (deltaPx / width) * spanTotal;

                tempsMinVue = timelineDragStartMin + deltaMs;
                tempsMaxVue = timelineDragStartMax + deltaMs;

                mettreAJourZoomUI();
                dessinerGraphique();
                dessinerFriseChronologique();
            }
        });

        // ==========================================
        // INFOBULLE ET SÉLECTEURS
        // ==========================================

        function mettreAJourTooltip(globalX, globalY) {
            const rect = chartWrapper.getBoundingClientRect();
            const plotW = rect.width - padLeft - padRight;
            if (hoverPixelX === null) {
                tooltip.style.display = "none";
                return;
            }

            const spanT = tempsMaxVue - tempsMinVue;
            const tempsSurvol = tempsMinVue + ((hoverPixelX - padLeft) / plotW) * spanT;

            const lignes = [];
            let dateTexte = "";

            Object.keys(seriesParCamera).forEach(nom => {
                if (!cameraVisibilite[nom]) return;
                const pts = seriesParCamera[nom];
                let ptProche = null;
                let minDist = Infinity;

                pts.forEach(p => {
                    const dist = Math.abs(p.time - tempsSurvol);
                    if (dist < minDist) {
                        minDist = dist;
                        ptProche = p;
                    }
                });

                if (ptProche) {
                    dateTexte = ptProche.localTime;
                    lignes.push({
                        nom: nom,
                        temp: ptProche.temp,
                        couleur: cameraCouleurs[nom],
                    });
                }
            });

            if (lignes.length === 0) {
                tooltip.style.display = "none";
                return;
            }

            let html = `<div class="tooltip-date">🕒 ${dateTexte}</div>`;
            lignes.forEach(l => {
                html += `
                    <div class="tooltip-row">
                        <span class="tooltip-camera-name">
                            <span class="tooltip-dot" style="background:${l.couleur};"></span>
                            ${l.nom}
                        </span>
                        <strong>${l.temp.toFixed(1)} ${UNITE_TEMP}</strong>
                    </div>
                `;
            });

            tooltip.innerHTML = html;
            tooltip.style.display = "block";

            const tooltipRect = tooltip.getBoundingClientRect();
            let posX = hoverPixelX + 15;
            let posY = (hoverPixelY || 50) - 20;

            if (posX + tooltipRect.width > rect.width - 10) {
                posX = hoverPixelX - tooltipRect.width - 15;
            }
            if (posY + tooltipRect.height > rect.height - 10) {
                posY = rect.height - tooltipRect.height - 10;
            }
            if (posY < 10) posY = 10;

            tooltip.style.left = posX + "px";
            tooltip.style.top = posY + "px";
        }

        function appliquerPlageDate() {
            const d1 = document.getElementById("input-date-debut").value;
            const d2 = document.getElementById("input-date-fin").value;
            if (d1 && d2) {
                const dateDebutIso = new Date(d1 + "T00:00:00").toISOString();
                const dateFinIso = new Date(d2 + "T23:59:59").toISOString();
                chargerHistorique(null, dateDebutIso, dateFinIso);
            } else if (!d1 && !d2) {
                // Champs vidés : retour à tout l'historique.
                chargerHistorique("all");
            }
        }

        function mettreAJourStats() {
            const tbody = document.getElementById("stats-table");
            const noms = Object.keys(seriesParCamera);
            if (noms.length === 0) {
                tbody.innerHTML = "<tr><td colspan='6' style='color:var(--text-muted);'>Pas de données.</td></tr>";
                return;
            }

            tbody.innerHTML = noms.map(nom => {
                if (!cameraVisibilite[nom]) return "";
                const pts = seriesParCamera[nom];
                const vals = pts.map(p => p.temp);
                if (vals.length === 0) return "";

                const min = Math.min(...vals).toFixed(1);
                const max = Math.max(...vals).toFixed(1);
                const avg = (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1);

                return `
                    <tr>
                        <td>
                            <span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:${cameraCouleurs[nom]}; margin-right:6px;"></span>
                            <strong>${nom}</strong>
                        </td>
                        <td>Blink Outdoor</td>
                        <td style="color:var(--primary); font-weight:600;">${min} ${UNITE_TEMP}</td>
                        <td style="color:#ffffff; font-weight:600;">${avg} ${UNITE_TEMP}</td>
                        <td style="color:var(--accent-orange); font-weight:600;">${max} ${UNITE_TEMP}</td>
                        <td>${vals.length}</td>
                    </tr>
                `;
            }).join("");
        }

        async function declencherReleve() {
            // Ne relever que les caméras affichées (cochées) sur le graphique
            const camerasCochees = Object.keys(cameraVisibilite).filter(nom => cameraVisibilite[nom]);
            if (camerasCochees.length === 0) {
                afficherToast("ℹ️ Aucune caméra affichée : cochez au moins une courbe avant de relever.");
                return;
            }

            const btn = document.getElementById("btn-refresh");
            btn.disabled = true;
            btn.textContent = "⏳ Relève en cours...";
            try {
                const res = await fetch("/api/refresh", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ cameras: camerasCochees }),
                });
                const r = await res.json();
                if (r.ok) {
                    const reveils = r.reveils && r.reveils.length
                        ? ` ${r.reveils.length} caméra(s) réveillée(s) : ${r.reveils.join(", ")}.`
                        : "";
                    afficherToast(`✅ Relevé réussi : ${r.count} caméra(s) actualisée(s).${reveils}`);
                    await chargerDonneesInitiales();
                } else {
                    afficherToast("⚠️ Erreur : " + (r.error || "Inconnue"));
                }
            } catch (err) {
                afficherToast("⚠️ Échec de connexion : " + err);
            } finally {
                btn.disabled = false;
                btn.textContent = "🔄 Relever maintenant";
            }
        }

        window.addEventListener("resize", redimensionnerCanvas);
        window.addEventListener("DOMContentLoaded", () => {
            redimensionnerCanvas();
            chargerReglages();
            chargerEtatMaj();
            chargerDonneesInitiales();
            setInterval(chargerDonneesInitiales, 60000);
        });
    </script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    storage: Storage
    lock: threading.Lock

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        chemin = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if chemin == "/" or chemin == "/index.html":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        if chemin == "/api/latest":
            data = self.storage.obtenir_dernieres_temperatures(outdoor_only=True)
            self._repondre_json(data)
            return

        if chemin == "/api/maj":
            force = query.get("force", ["0"])[0] in ("1", "true", "oui")
            updater.verifier_async(force=force)
            self._repondre_json(updater.etat())
            return

        if chemin == "/api/history":
            raw_h = query.get("hours", ["24"])[0]
            heures = int(raw_h) if raw_h.isdigit() else (None if raw_h in ("all", "0", "") else 24)
            debut = query.get("start", [None])[0]
            fin = query.get("end", [None])[0]
            cam = query.get("camera", [None])[0]
            data = self.storage.obtenir_historique(
                camera=cam, heures=heures, debut=debut, fin=fin, outdoor_only=True
            )
            self._repondre_json(data)
            return

        if chemin == "/api/visibilite":
            data = config.charger_config().get("visibilite_cameras", {})
            self._repondre_json(data)
            return

        if chemin == "/api/reglages":
            cfg = config.charger_config()
            self._repondre_json({
                "reveiller_cameras": bool(cfg.get("reveiller_cameras", False)),
                "dernier_reveil": cfg.get("dernier_reveil", 0),
            })
            return

        if chemin == "/api/stats":
            heures = int(query.get("hours", ["24"])[0])
            data = self.storage.obtenir_statistiques(heures=heures, outdoor_only=True)
            self._repondre_json(data)
            return

        if chemin == "/api/export.csv":
            temp_file = paths.dossier_donnees() / "export_temp.csv"
            self.storage.exporter_csv(temp_file)
            contenu = temp_file.read_bytes()
            temp_file.unlink(missing_ok=True)

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="temperatures_outdoor.csv"')
            self.end_headers()
            self.wfile.write(contenu)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Page introuvable")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/maj":
            try:
                updater.installer_async()
            except updater.UpdaterError as err:
                self._repondre_json(
                    {"ok": False, "erreur": str(err), **updater.etat()},
                    status=HTTPStatus.CONFLICT,
                )
                return
            self._repondre_json(
                {"ok": True, **updater.etat()}, status=HTTPStatus.ACCEPTED
            )
            return

        if parsed.path == "/api/reglages":
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
                brut = self.rfile.read(length) if length else b"{}"
                data = json.loads(brut.decode("utf-8"))
            except (ValueError, json.JSONDecodeError) as err:
                self._repondre_json({"ok": False, "error": f"JSON invalide : {err}"}, status=HTTPStatus.BAD_REQUEST)
                return
            if not isinstance(data, dict):
                self._repondre_json({"ok": False, "error": "Objet JSON attendu."}, status=HTTPStatus.BAD_REQUEST)
                return

            if "reveiller_cameras" in data:
                valeur = data["reveiller_cameras"]
                if not isinstance(valeur, bool):
                    self._repondre_json(
                        {"ok": False, "error": "reveiller_cameras doit être un booléen."},
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                config.modifier_config(reveiller_cameras=valeur)

            cfg = config.charger_config()
            self._repondre_json({
                "ok": True,
                "reveiller_cameras": bool(cfg.get("reveiller_cameras", False)),
            })
            return

        if parsed.path == "/api/visibilite":
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
                brut = self.rfile.read(length) if length else b"{}"
                data = json.loads(brut.decode("utf-8"))
            except (ValueError, json.JSONDecodeError) as err:
                self._repondre_json({"ok": False, "error": f"JSON invalide : {err}"}, status=HTTPStatus.BAD_REQUEST)
                return

            # Normalisation : {nom_camera: booléen}
            visibilite = {str(nom): bool(valeur) for nom, valeur in data.items()} if isinstance(data, dict) else {}
            config.modifier_config(visibilite_cameras=visibilite)
            self._repondre_json({"ok": True, "count": len(visibilite)})
            return

        if parsed.path == "/api/refresh":
            # Liste optionnelle de caméras ciblées (noms affichés/cochés côté page)
            cameras_json = None
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
                if length:
                    data = json.loads(self.rfile.read(length).decode("utf-8"))
                    if isinstance(data, dict) and isinstance(data.get("cameras"), list):
                        cameras_json = [str(n) for n in data["cameras"]]
            except (ValueError, json.JSONDecodeError):
                cameras_json = None  # corps invalide -> relevé sans filtre (comportement historique)

            try:
                cfg = config.charger_config()
                reveils: list[str] = []
                # Exécution synchrone protégée par verrou
                with self.lock:
                    releves = asyncio.run(collector.relever_une_fois(
                        storage=self.storage, outdoor_only=True, interactive=False,
                        cameras_ciblees=cameras_json,
                        reveiller=bool(cfg.get("reveiller_cameras", False)),
                        forcer_reveil=True,
                        reveils_effectues=reveils,
                    ))
                self._repondre_json({"ok": True, "count": len(releves), "reveils": reveils})
            except Exception as err:
                self._repondre_json({"ok": False, "error": str(err)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def _repondre_json(self, donnees: Any, status: HTTPStatus = HTTPStatus.OK):
        texte = json.dumps(donnees, ensure_ascii=False)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(texte.encode("utf-8"))

    def log_message(self, format, *args):
        # Silence HTTP access logs on terminal to keep output clean
        pass


def demarrer_serveur_web(storage: Storage, port: int = 8770, daemon: bool = True) -> ThreadingHTTPServer:
    """Démarre le serveur HTTP du tableau de bord dans un thread d'arrière-plan."""
    lock = threading.Lock()

    class HandlerAvecDep(DashboardHandler):
        def __init__(self, *args, **kwargs):
            self.storage = storage
            self.lock = lock
            super().__init__(*args, **kwargs)

    serveur = None
    derniere_erreur: OSError | None = None
    # Après une mise à jour, le nouveau processus démarre alors que l'ancien
    # vient de rendre le port : quelques secondes de patience suffisent.
    for _ in range(30):
        try:
            serveur = ThreadingHTTPServer(("0.0.0.0", port), HandlerAvecDep)
            break
        except OSError as err:
            derniere_erreur = err
            time.sleep(1)
    if serveur is None:
        raise derniere_erreur or OSError(f"Port {port} indisponible")

    thread = threading.Thread(target=serveur.serve_forever, daemon=daemon)
    thread.start()
    return serveur
