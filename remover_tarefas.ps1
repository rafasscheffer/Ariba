$names = @(
    "Brasmo - Monitor Ariba - Logon",
    "Brasmo - Monitor Ariba - Tarde"
)

foreach ($name in $names) {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($task) {
        Unregister-ScheduledTask -TaskName $name -Confirm:$false
        Write-Host "Removida: $name"
    }
}
