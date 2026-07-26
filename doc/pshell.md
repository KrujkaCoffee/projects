# дд

```shell

$expires = [datetime]::FromFileTime($user."msDS-UserPasswordExpiryTimeComputed")
$daysLeft = ($expires - (Get-Date)).Days

"Пароль истекает: $expires"
"Осталось дней: $daysLeft"
```