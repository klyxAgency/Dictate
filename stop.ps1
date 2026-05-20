Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" | Where-Object { $_.CommandLine -match 'dictate\.py' } | Invoke-CimMethod -MethodName Terminate
