# Dynamic Data Management

## Data Files Location

सभी dynamic data JSON files यहाँ स्थित हैं:

```
govt-exam-backend/
├── data/
│   ├── announcements.json    (Ticker announcements)
│   ├── bulletins.json        (Official bulletins)
│   └── analytics.json        (System metrics)
```

## Data Files Structure

### 1. Announcements (`data/announcements.json`)
**Location**: `govt-exam-backend/data/announcements.json`

यह file ticker में दिखने वाले announcements contain करती है।

**Structure**:
```json
{
  "announcements": [
    {
      "id": "unique-id",
      "title": "Announcement Title",
      "description": "Announcement description text",
      "icon": "⚠️",
      "link": "#"
    }
  ]
}
```

### 2. Bulletins (`data/bulletins.json`)
**Location**: `govt-exam-backend/data/bulletins.json`

यह file "Official Gazette & Bulletins" section में दिखने वाली bulletins contain करती है।

**Structure**:
```json
{
  "bulletins": [
    {
      "id": "unique-id",
      "date": "June 05, 2026",
      "title": "Bulletin title",
      "link": "#",
      "is_new": true
    }
  ]
}
```

### 3. Analytics (`data/analytics.json`)
**Location**: `govt-exam-backend/data/analytics.json`

यह file "System Telemetry Analytics" section में दिखने वाले metrics contain करती है।

**Structure**:
```json
{
  "metrics": [
    {
      "label": "32,679",
      "description": "Monitored Open Posts",
      "value": "posts"
    }
  ]
}
```

## Data को Update करने के तरीके

### Method 1: JSON files को directly edit करें
1. `govt-exam-backend/data/` folder खोलें
2. Required JSON file को edit करें
3. Save करें
4. Backend auto-reload होगा या restart करें

### Method 2: Backend API से update करें (Admin Endpoints)

Admin endpoints के through data update कर सकते हैं:

```bash
# Update Announcements
curl -X POST http://localhost:8000/admin/announcements \
  -H "Content-Type: application/json" \
  -d '{"announcements": [...]}'

# Update Bulletins
curl -X POST http://localhost:8000/admin/bulletins \
  -H "Content-Type: application/json" \
  -d '{"bulletins": [...]}'

# Update Analytics
curl -X POST http://localhost:8000/admin/analytics \
  -H "Content-Type: application/json" \
  -d '{"metrics": [...]}'
```

### Method 3: Frontend से admin panel के through (future)
Later एक admin panel बना सकते हैं जो ये endpoints use करे।

## Frontend Endpoints

Frontend इन endpoints से data fetch करता है:

- `GET /announcements` - Ticker announcements
- `GET /bulletins` - Official bulletins
- `GET /analytics` - System metrics

सभी data skeleton loading के साथ fetch होता है।

## Example: Announcements Update करना

### JSON file सीधे edit करें:

```json
{
  "announcements": [
    {
      "id": "new-announcement",
      "title": "नई परीक्षा घोषणा",
      "description": "यह नई परीक्षा की जानकारी है",
      "icon": "📣",
      "link": "#"
    }
  ]
}
```

फिर browser refresh करें, नया announcement ticker में दिखेगा।

## Important Notes

- Data files JSON format में होनी चाहिए
- Special characters के लिए UTF-8 encoding use करें
- Admin endpoints में proper validation add करने की जरूरत है (production के लिए)
- Backup regularly रखें!
