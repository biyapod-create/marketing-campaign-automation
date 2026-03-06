# Enrich leads via Apollo org enrichment + write to leads_database.csv
# Load API key from .env file (never hardcode keys here)
$envFile = Join-Path $PSScriptRoot '.env'
$key = if (Test-Path $envFile) {
    (Get-Content $envFile | Select-String 'APOLLO_IO_API_KEY').ToString().Split('=',2)[1].Trim()
} else { $env:APOLLO_IO_API_KEY }
if (-not $key) { throw "APOLLO_IO_API_KEY not set. Add it to your .env file." }
$headers = @{ 'x-api-key' = $key; 'Content-Type' = 'application/json' }

# Leads from Google Places (Abuja) - name, best-guess domain, category, address
$rawLeads = @(
    @{ name='Tar Tar'; domains=@('tartartabuja.com','tartar.ng'); cat='restaurant'; addr='Wuse 2, Abuja'; rating=4.4; reviews=481 },
    @{ name='Village Chief Restaurant'; domains=@('villagechief.ng','villagechiefrestarant.com'); cat='restaurant'; addr='Wuse 2, Abuja'; rating=4.2; reviews=3564 },
    @{ name='Cantina Restaurant'; domains=@('cantinaabuja.com','cantina.ng'); cat='restaurant'; addr='Maitama, Abuja'; rating=4.3; reviews=1685 },
    @{ name='Duo Restaurant'; domains=@('duorestaurant.ng','duoabuja.com'); cat='restaurant'; addr='Wuse 2, Abuja'; rating=4.2; reviews=1761 },
    @{ name='Kapadoccia Abuja'; domains=@('kapadoccia.ng','kapadocciaabuja.com'); cat='restaurant'; addr='Wuse 2, Abuja'; rating=4.3; reviews=773 },
    @{ name='Foodies Hot and Spicy'; domains=@('foodiesabuja.com','foodies.ng'); cat='restaurant'; addr='Maitama, Abuja'; rating=4.4; reviews=72 },
    @{ name='Kashco Restaurant'; domains=@('kashco.ng','kashcorestaurant.com'); cat='restaurant'; addr='Wuse 2, Abuja'; rating=4.9; reviews=64 },
    @{ name='Beauty Emporia'; domains=@('beautyemporia.ng','beautyemporiaabuja.com'); cat='salon'; addr='Asokoro, Abuja'; rating=4.9; reviews=134 },
    @{ name='Annish Unisex Salon'; domains=@('annishsalon.ng','annishsalon.com'); cat='salon'; addr='Wuse 2, Abuja'; rating=4.8; reviews=251 },
    @{ name='Ventures Park'; domains=@('venturespark.co'); cat='coworking'; addr='Maitama, Abuja'; rating=4.5; reviews=612 },
    @{ name='Space Station Nigeria'; domains=@('spacestationng.com','spacestation.ng'); cat='coworking'; addr='Wuse, Abuja'; rating=4.8; reviews=21 },
    @{ name='Work and Connect'; domains=@('workandconnect.ng','workandconnect.com'); cat='coworking'; addr='Jabi, Abuja'; rating=4.3; reviews=318 },
    @{ name='Enspire Incubator'; domains=@('enspire.ng','enspireng.com'); cat='incubator'; addr='Maitama, Abuja'; rating=4.4; reviews=34 },
    @{ name='Seedbuilders Innovation Hub'; domains=@('seedbuilders.ng','seedbuildersng.com'); cat='hub'; addr='Wuse 2, Abuja'; rating=4.5; reviews=118 }
)

$results = @()

foreach ($lead in $rawLeads) {
    $enriched = $null
    $matchedDomain = $null

    # Try each domain guess until one returns data
    foreach ($domain in $lead.domains) {
        try {
            $r = Invoke-RestMethod -Uri "https://api.apollo.io/api/v1/organizations/enrich?domain=$domain" -Method GET -Headers $headers -ErrorAction Stop
            if ($r -and $r.organization -and $r.organization.name) {
                $enriched = $r.organization
                $matchedDomain = $domain
                break
            }
        } catch {
            # domain not found, try next
            continue
        }
    }

    if ($enriched) {
        $results += [PSCustomObject]@{
            company_name    = $enriched.name
            domain          = $matchedDomain
            city            = if ($enriched.city) { $enriched.city } else { 'Abuja' }
            country         = if ($enriched.country) { $enriched.country } else { 'Nigeria' }
            industry        = $enriched.industry
            employees       = $enriched.estimated_num_employees
            linkedin        = $enriched.linkedin_url
            source          = 'google_places'
            category        = $lead.cat
            google_rating   = $lead.rating
            google_reviews  = $lead.reviews
            status          = 'enriched'
            notes           = 'Apollo enrichment hit'
        }
        Write-Host "HIT  | $($enriched.name) | $matchedDomain | $($enriched.industry) | $($enriched.estimated_num_employees) employees"
    } else {
        # No Apollo data - still add from Google Places data
        $results += [PSCustomObject]@{
            company_name    = $lead.name
            domain          = ''
            city            = 'Abuja'
            country         = 'Nigeria'
            industry        = $lead.cat
            employees       = ''
            linkedin        = ''
            source          = 'google_places'
            category        = $lead.cat
            google_rating   = $lead.rating
            google_reviews  = $lead.reviews
            status          = 'needs_manual_contact'
            notes           = 'No Apollo match - needs manual email lookup'
        }
        Write-Host "MISS | $($lead.name) | no domain match"
    }
}

# Write CSV
$csvPath = 'C:\Users\Allen\Desktop\Marketing Campaign\leads_database.csv'
$results | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
Write-Host ""
Write-Host "=== DONE ==="
Write-Host "Total leads written: $($results.Count)"
Write-Host "Enriched: $(($results | Where-Object { $_.status -eq 'enriched' }).Count)"
Write-Host "Needs manual: $(($results | Where-Object { $_.status -eq 'needs_manual_contact' }).Count)"
Write-Host "CSV saved to: $csvPath"
