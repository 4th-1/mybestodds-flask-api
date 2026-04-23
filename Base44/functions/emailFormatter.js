/**
 * BASE44 EMAIL FORMATTER
 * 
 * Formats predictions into structured email matching Excel deliverable format
 * Based on: jackpot_system_v3/make_final_sheet.py structure
 */

// Official Lottery Odds Map
const OFFICIAL_ODDS = {
  'Cash3': '1 in 1,000',
  'Cash4': '1 in 10,000',
  'Millionaire For Life': '1 in 21,846,048',
  'MegaMillions': '1 in 302,575,350',
  'Powerball': '1 in 292,201,338'
};

// Verdict color mapping (matching Excel colors)
const VERDICT_COLORS = {
  'STRONG PLAY': { bg: '#DCFCE7', text: '#166534', emoji: '🟢' },  // Green
  'GREEN': { bg: '#DCFCE7', text: '#166534', emoji: '🟢' },
  'MODERATE': { bg: '#FEF9C3', text: '#854D0E', emoji: '🟨' },      // Yellow
  'YELLOW': { bg: '#FEF9C3', text: '#854D0E', emoji: '🟨' },
  'WATCH': { bg: '#F3F4F6', text: '#9CA3AF', emoji: '⚪' },        // Gray
  'RED': { bg: '#FEE2E2', text: '#991B1B', emoji: '🔴' }
};

/**
 * Format predictions for email display
 * @param {Array} predictions - Array of prediction objects from Flask API
 * @param {Object} subscriber - Subscriber info
 * @param {String} frequency - Email frequency (daily, weekly, twice_weekly)
 * @returns {String} Formatted HTML email content
 */
export function formatPredictionsEmail(predictions, subscriber, frequency = 'daily') {
  // Group predictions by date, then game, then session
  const groupedByDate = groupPredictionsByDate(predictions);
  const dates = Object.keys(groupedByDate).sort();
  const isMultiDay = frequency === 'weekly' || frequency === 'twice_weekly';
  
  let emailHtml = `
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 800px; margin: 0 auto; background: #0A1929; color: #E2E8F0; padding: 20px;">
      
      <!-- Header -->
      <div style="text-align: center; padding: 30px 0; border-bottom: 2px solid #1E293B;">
        <h1 style="color: #10B981; margin: 0; font-size: 32px;">${getEmailTitle(frequency, dates)}</h1>
        <p style="color: #94A3B8; margin: 10px 0 0 0;">Hi ${subscriber.full_name || subscriber.name},</p>
      </div>
      
      ${isMultiDay ? `
      <!-- Multi-Day Overview -->
      <div style="background: #1E293B; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #10B981;">
        <h3 style="color: #10B981; margin: 0 0 10px 0;">📅 Your Upcoming Predictions</h3>
        <p style="color: #94A3B8; margin: 5px 0;">${dates.length} days of predictions ready</p>
        <p style="color: #64748B; margin: 5px 0; font-size: 14px;">${formatDateRange(dates[0], dates[dates.length - 1])}</p>
      </div>
      ` : `
      <!-- Today's Conditions -->
      <div style="background: #1E293B; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #6366F1;">
        <h3 style="color: #C7D2FE; margin: 0 0 10px 0;">TODAY'S CONDITIONS</h3>
        <p style="color: #94A3B8; margin: 5px 0;">1.00x BASELINE conditions - standard probability</p>
        <p style="color: #64748B; margin: 5px 0; font-size: 14px;">Standard probability - Minimal play</p>
      </div>
      `}
      
      <!-- Predictions Table Header -->
      <div style="margin: 30px 0 20px 0;">
        <h2 style="color: #10B981; border-bottom: 2px solid #10B981; padding-bottom: 10px;">📊 YOUR PERSONALIZED PREDICTIONS</h2>
      </div>
  `;
  
  // Process each date
  for (const date of dates) {
    const dateData = groupedByDate[date];
    
    // Show date headers for multi-day emails
    if (isMultiDay) {
      emailHtml += `
        <div style="margin: 30px 0 15px 0;">
          <h2 style="color: #10B981; background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); padding: 15px; border-radius: 8px; border-left: 4px solid #10B981;">
            📅 ${formatDateHeader(date)}
          </h2>
        </div>
      `;
    }
    
    emailHtml += `<div style="margin: 20px 0;">`;
    
    // Process each game for this date
    const gameNames = Object.keys(dateData.games).sort();
    for (const game of gameNames) {
      const gameData = dateData.games[game];
      emailHtml += formatGameSection(game, gameData, date);
    }
    
    emailHtml += `</div>`;
  }
  
  // Call-to-Action Button
  emailHtml += `
      <!-- Dashboard CTA -->
      <div style="text-align: center; margin: 30px 0;">
        <a href="${process.env.BASE44_APP_URL || 'https://mybestodds.net'}/dashboard" style="
          display: inline-block;
          background: linear-gradient(135deg, #10B981 0%, #059669 100%);
          color: #FFFFFF;
          padding: 18px 40px;
          border-radius: 12px;
          text-decoration: none;
          font-weight: bold;
          font-size: 18px;
          box-shadow: 0 4px 6px rgba(16, 185, 129, 0.4);
          transition: all 0.3s ease;
        ">
          🎯 VIEW FULL DASHBOARD
        </a>
        <p style="color: #94A3B8; margin: 15px 0 0 0; font-size: 14px;">
          See overlay analysis, confidence charts, and historical performance
        </p>
      </div>
  `;

  // Footer Legend
  emailHtml += `
      <!-- Legend -->
      <div style="background: #1E293B; padding: 20px; margin: 30px 0 0 0; border-radius: 8px;">
        <h3 style="color: #94A3B8; margin: 0 0 15px 0; font-size: 16px;">LEGEND</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
          <div><span style="color: #10B981;">🟢 STRONG PLAY</span> = 70%+ engine confidence (HIGH)</div>
          <div><span style="color: #FCD34D;">🟨 MODERATE</span> = 40–69% engine confidence</div>
          <div><span style="color: #9CA3AF;">⚪ WATCH</span> = &lt;40% engine confidence (LOW)</div>
        </div>
        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #334155; color: #64748B; font-size: 12px;">
          <strong>Method:</strong> SMART Logic (v3.7 Engine) | <strong>Kit:</strong> ${subscriber.kit_type || 'BOOK3'}
        </div>
      </div>
      
      <!-- Footer Links -->
      <div style="text-align: center; padding: 20px 0; border-top: 1px solid #1E293B; margin-top: 30px;">
        <p style="color: #64748B; font-size: 12px; margin: 0 0 10px 0;">
          <a href="${process.env.BASE44_APP_URL || 'https://mybestodds.net'}/dashboard" style="color: #10B981; text-decoration: none;">Dashboard</a> •
          <a href="${process.env.BASE44_APP_URL || 'https://mybestodds.net'}/settings" style="color: #10B981; text-decoration: none;">Settings</a> •
          <a href="${process.env.BASE44_APP_URL || 'https://mybestodds.net'}/history" style="color: #10B981; text-decoration: none;">Win History</a>
        </p>
        <p style="color: #475569; font-size: 11px; margin: 5px 0 0 0;">
          Questions? Reply to this email or visit our <a href="${process.env.BASE44_APP_URL || 'https://mybestodds.net'}/support" style="color: #10B981;">Support Center</a>
        </p>
      </div>
      
    </div>
  `;
  
  return emailHtml;
}

/**
 * Format a single game section (matches Excel row format)
 */
function formatGameSection(game, gameData, date) {
  const officialOdds = OFFICIAL_ODDS[game] || 'N/A';
  let html = `
    <div style="margin: 15px 0; background: #0F172A; border-radius: 8px; overflow: hidden; border: 1px solid #1E293B;">
      <!-- Game Header -->
      <div style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); padding: 15px; border-bottom: 2px solid #10B981;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <h3 style="margin: 0; color: #10B981; font-size: 20px;">${getGameIcon(game)} ${game}</h3>
          <span style="color: #64748B; font-size: 12px;">Official Odds: ${officialOdds}</span>
        </div>
      </div>
      
      <!-- Table Header -->
      <div style="display: grid; grid-template-columns: 100px 120px 1fr 80px 100px; gap: 10px; padding: 10px 15px; background: #1E293B; font-weight: bold; font-size: 12px; color: #94A3B8; border-bottom: 1px solid #334155;">
        <div>SESSION</div>
        <div>NUMBERS</div>
        <div>PLAY TYPE</div>
        <div>CONFIDENCE</div>
        <div>VERDICT</div>
      </div>
  `;
  
  // Sessions in order
  const sessionOrder = ['MIDDAY', 'EVENING', 'NIGHT'];
  
  for (const session of sessionOrder) {
    const sessionPreds = gameData.sessions[session];
    if (!sessionPreds || sessionPreds.length === 0) continue;
    
    // Process each prediction in this session
    for (const pred of sessionPreds) {
      // Accept both legacy 'confidence' and new engine 'confidence_score' fields
      const rawConf = pred.confidence_score ?? pred.confidence ?? null;
      const normPct = normaliseConfidence(rawConf);
      const band = pred.band || getConfidenceBand(normPct);
      const verdict = determineVerdict(rawConf, band);
      const verdictStyle = VERDICT_COLORS[verdict] || VERDICT_COLORS['WATCH'];
      
      html += `
        <div style="display: grid; grid-template-columns: 100px 120px 1fr 80px 100px; gap: 10px; padding: 12px 15px; border-bottom: 1px solid #1E293B; align-items: center;">
          <!-- Session -->
          <div style="color: #60A5FA; font-weight: 600; font-size: 11px;">${session}</div>
          
          <!-- Numbers (preserve leading zeros) -->
          <div style="font-family: 'Courier New', monospace; font-size: 18px; font-weight: bold; color: #FCD34D; letter-spacing: 1px;">
            ${formatNumbers(pred.numbers, game)}
          </div>
          
          <!-- Play Type -->
          <div style="color: #94A3B8; font-size: 13px;">
            ${pred.play_type || 'STRAIGHT'}
            ${pred.method ? `<span style="color: #64748B; font-size: 11px; display: block;">Method: ${pred.method}</span>` : ''}
          </div>
          
          <!-- Confidence -->
          <div style="text-align: center; font-weight: bold; color: #10B981; font-size: 14px;">
            ${formatConfidence(rawConf)}
          </div>
          
          <!-- Verdict -->
          <div style="text-align: center;">
            <span style="background: ${verdictStyle.bg}; color: ${verdictStyle.text}; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; display: inline-block;">
              ${verdictStyle.emoji} ${verdict}
            </span>
          </div>
        </div>
      `;
    }
  }
  
  html += `</div>`;
  return html;
}

/**
 * Group predictions by date -> game -> session
 */
function groupPredictionsByDate(predictions) {
  const grouped = {};
  
  for (const pred of predictions) {
    const date = pred.date || pred.draw_date;
    const game = pred.game;
    const session = pred.session || 'EVENING';
    
    if (!grouped[date]) {
      grouped[date] = { games: {} };
    }
    
    if (!grouped[date].games[game]) {
      grouped[date].games[game] = { sessions: {} };
    }
    
    if (!grouped[date].games[game].sessions[session]) {
      grouped[date].games[game].sessions[session] = [];
    }
    
    grouped[date].games[game].sessions[session].push(pred);
  }
  
  return grouped;
}

/**
 * Normalise a confidence value to 0–100 range.
 * Accepts either a 0–1 decimal (engine output) or a 0–100 percentage.
 */
function normaliseConfidence(confidence) {
  if (typeof confidence !== 'number') return null;
  // Values ≤ 1.0 are decimal fractions from the engine
  return confidence <= 1.0 ? confidence * 100 : confidence;
}

/**
 * Return the band label (HIGH / MODERATE / LOW) for a normalised 0–100 score.
 */
function getConfidenceBand(normalisedPct) {
  if (normalisedPct === null) return 'MODERATE';
  if (normalisedPct >= 70) return 'HIGH';
  if (normalisedPct >= 40) return 'MODERATE';
  return 'LOW';
}

/**
 * Determine verdict based on confidence and band.
 * Accepts both 0–1 decimal and 0–100 percentage for confidence.
 */
function determineVerdict(confidence, band) {
  if (band === 'GREEN') return 'STRONG PLAY';
  if (band === 'RED') return 'WATCH';
  const pct = normaliseConfidence(confidence);
  if (pct !== null) {
    if (pct >= 70) return 'STRONG PLAY';
    if (pct >= 40) return 'MODERATE';
    return 'WATCH';
  }
  if (band === 'YELLOW') return 'MODERATE';
  return 'MODERATE';
}

/**
 * Format numbers with leading zeros preserved
 */
function formatNumbers(numbers, game) {
  const numStr = String(numbers).trim();
  
  // Cash3: ensure 3 digits
  if (game === 'Cash3' && numStr.length < 3) {
    return numStr.padStart(3, '0');
  }
  
  // Cash4: ensure 4 digits
  if (game === 'Cash4' && numStr.length < 4) {
    return numStr.padStart(4, '0');
  }
  
  // Jackpot games: format with spacing
  if (game === 'Cash4Life' || game === 'Millionaire For Life' || game === 'MegaMillions' || game === 'Powerball') {
    // Already formatted from API (e.g., "04-15-31-51-56 + CB:03")
    return numStr;
  }
  
  return numStr;
}

/**
 * Format confidence as percentage.
 * Accepts 0–1 decimal (engine output) or 0–100 percentage.
 */
function formatConfidence(confidence) {
  const pct = normaliseConfidence(confidence);
  if (pct !== null) return `${pct.toFixed(1)}%`;
  return '—';
}

/**
 * Get game icon
 */
function getGameIcon(game) {
  const icons = {
    'Cash3': '💵',
    'Cash4': '💵',
    'Millionaire For Life': '💰',
    'MegaMillions': '🎰',
    'Powerball': '🎲'
  };
  return icons[game] || '🎯';
}

/**
 * Format date for display
 */
function formatDate(date) {
  return date.toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric' 
  });
}

/**
 * Format date header
 */
function formatDateHeader(dateStr) {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { 
    weekday: 'short',
    month: 'short', 
    day: 'numeric',
    year: 'numeric'
  });
}

/**
 * Get email title based on frequency
 */
function getEmailTitle(frequency, dates) {
  if (frequency === 'weekly') {
    return `Your Week of Predictions`;
  } else if (frequency === 'twice_weekly') {
    return `Your Next 3 Days`;
  }
  // Daily
  const firstDate = dates.length > 0 ? new Date(dates[0]) : new Date();
  return `Your ${formatDate(firstDate)} Predictions`;
}

/**
 * Format date range display
 */
function formatDateRange(startStr, endStr) {
  const start = new Date(startStr);
  const end = new Date(endStr);
  return `${formatDateShort(start)} - ${formatDateShort(end)}`;
}

/**
 * Format date short (for ranges)
 */
function formatDateShort(date) {
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Export for Base44 usage
export default {
  formatPredictionsEmail,
  OFFICIAL_ODDS,
  VERDICT_COLORS
};
