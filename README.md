# MySchoolApp Assignment Fetcher

A script built with Selenium + Requests to fetch assignments from MySchoolApp (Blackbaud). It automates browser login (supports Google SSO), extracts the required cookies/tokens, and then uses requests to call:

```
GET /api/assignment2/StudentAssignmentCenterGet?displayByDueDate=true
```

to retrieve assignment data.

> ⚠️ For learning and personal backup use only.

## Features

- Launches Chrome and logs in (includes locating/clicking the Continue with Google button — the first login is manual).
- Reads cookies/tokens from the authenticated browser session.
- Uses requests to call the official API and obtain the assignment list.
- Can save the raw JSON to disk for further processing.
  
## Requirements

- Python 3.9+ (3.10/3.11 recommended)
- Google Chrome (latest)
- Internet access
