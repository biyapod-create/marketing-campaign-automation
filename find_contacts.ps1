# Script to find contact emails for Abuja businesses via web scraping
# For each business, search Google for "[business name] Abuja contact email owner"
# and extract email addresses from results

$businesses = @(
    'Tar Tar Restaurant Abuja contact email owner',
    'Village Chief Restaurant Abuja contact email owner',
    'Cantina Restaurant Abuja Maitama contact email',
    'Duo Restaurant Abuja contact email owner',
    'Kapadoccia Restaurant Abuja contact email',
    'Foodies Hot and Spicy Restaurant Abuja contact',
    'Kashco Restaurant Cafe Abuja contact email',
    'Beauty Emporia Abuja salon contact email owner',
    'Annish Unisex Salon Abuja contact email owner',
    'Ventures Park Abuja coworking contact email owner',
    'Space Station Nigeria Abuja contact email',
    'Work and Connect Abuja coworking contact email owner',
    'Enspire Incubator Abuja contact email',
    'Seedbuilders Innovation Hub Abuja contact email owner'
)

foreach ($biz in $businesses) {
    Write-Host "SEARCH: $biz"
}
Write-Host "Ready for web scraping"
