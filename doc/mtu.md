```

Get-NetIPInterface | Sort-Object InterfaceAlias | Format-Table InterfaceAlias, AddressFamily, NlMtu, InterfaceMetric -Auto
```


```
Get-NetIPInterface -AddressFamily IPv4 | Format-Table InterfaceAlias, NlMtu, InterfaceMetric -Auto
```


```
Get-NetIPInterface -InterfaceAlias "Ethernet" | Format-Table InterfaceAlias, AddressFamily, NlMtu
```
```
Set-NetIPInterface -InterfaceAlias "Ethernet 3" -AddressFamily IPv4 -NlMtuBytes 1320
```
