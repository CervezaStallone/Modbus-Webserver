# Bootstrap en Chart.js Offline Download Instructies

## Benodigde bestanden

### Bootstrap 5
Download van: https://getbootstrap.com/docs/5.3/getting-started/download/

Benodigde bestanden:
- `bootstrap.min.css` -> plaats in `static/css/`
- `bootstrap.bundle.min.js` -> plaats in `static/js/`

### Chart.js
Download van: https://www.chartjs.org/docs/latest/getting-started/installation.html

Benodigde bestanden:
- `chart.min.js` (versie 4.x) -> plaats in `static/js/`

### Download commando's:

```bash
# Bootstrap CSS
curl -o static/css/bootstrap.min.css https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css

# Bootstrap JS
curl -o static/js/bootstrap.bundle.min.js https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js

# Chart.js
curl -o static/js/chart.min.js https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js

# ApexCharts (voor gauges, radial bars, etc.)
curl -o static/js/apexcharts.min.js https://cdn.jsdelivr.net/npm/apexcharts@3.45.1/dist/apexcharts.min.js
```

Of met wget:
```bash
wget -O static/css/bootstrap.min.css https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css
wget -O static/js/bootstrap.bundle.min.js https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js
wget -O static/js/chart.min.js https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js
```

Of met PowerShell:
```powershell
Invoke-WebRequest -Uri https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css -OutFile static/css/bootstrap.min.css
Invoke-WebRequest -Uri https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js -OutFile static/js/bootstrap.bundle.min.js
Invoke-WebRequest -Uri https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js -OutFile static/js/chart.min.js
```

## Alternatief: Gebruik CDN tijdelijk

Voor development kun je ook tijdelijk CDN links gebruiken in de templates:

```html
<!-- Bootstrap CSS -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">

<!-- Bootstrap JS -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>

<!-- Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
```
