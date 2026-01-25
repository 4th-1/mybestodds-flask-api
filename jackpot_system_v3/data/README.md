# Subscriber Data Directory

This directory contains subscriber configuration files for the My Best Odds prediction engine.

## Structure

- `subscribers/BOOK3/` - BOOK3 tier subscribers (Cash3 + Cash4 + All Jackpots)
- `subscribers/BOOK/` - BOOK tier subscribers (Jackpots only)
- `subscribers/BOSK/` - BOSK tier subscribers (Cash3 + Cash4 only)

New subscribers are dynamically handled via API - no manual file management required.
