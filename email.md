# State.gov WAF whitelist request

Send via the contact form at https://www.state.gov/contact-us/ (no publicly listed webmaster@ address; the form routes to the appropriate team).

---

**Subject:** Request to whitelist `JTFNews/1.0` bot on state.gov press-releases endpoint

**Body:**

Hello,

I operate JTF News (https://jtfnews.org), a non-profit, non-commercial news service that publishes only facts verified by two or more unrelated sources. The US State Department is one of the 22 primary sources our system checks every 30 minutes for public press releases.

As of 2026-09-03, the following URLs began returning HTTP 403 from your Akamai edge for our identified user agent `JTFNews/1.0`:

- https://www.state.gov/press-releases/
- https://www.state.gov/rss-feed/press-releases/feed/
- https://www.state.gov/robots.txt

The response body is your standard "Technical Difficulties" HTML page rather than the requested content. The same URLs return 200 for browser user agents, and the served robots.txt (when reachable) contains `User-agent: * / Disallow:` — i.e., your stated crawl policy explicitly permits us.

Rather than spoof a browser User-Agent — which would conflict with our project's honest-identification rule — we have disabled the State Department as a source until the WAF rule can be adjusted.

Request: please allow the following user-agent strings through the WAF for the `state.gov` press-releases and RSS endpoints:

- `JTFNews/1.0 (Facts only, no opinions; RSS reader)`
- `JTFNews/1.0-bot (+https://jtfnews.org)`

Our access pattern is 48 GETs per day per URL (once every 30 minutes), no POSTs, no login, honors your published robots.txt and `crawl-delay: 5`.

Happy to provide our source IP range or coordinate any other verification.

Thank you,
Larry Seyer
larryseyer@gmail.com
JTF News — https://jtfnews.org
Project source: https://github.com/JTFNews/jtfnews
