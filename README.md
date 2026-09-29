# NFL Betting Model ETL

Automated NFL team-stat ETL for the Google Sheet `Betting Model`.

## Sources
- nflverse weekly team statistics
- nflverse play-by-play
- nflverse schedule/results
- ESPN supplemental statistics

## Destination
Google Sheet:
`Betting Model`

## Automation
The production ETL will run with GitHub Actions.

## Important
Google credentials are stored only as encrypted GitHub Actions secrets.
No credentials are committed to this public repository.
