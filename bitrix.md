### Удалить диалог с юзером

```php
\Bitrix\Main\Loader::includeModule('im');

$userId1 = 1466;
$userId2 = 3076;

$chat = \Bitrix\Im\V2\Entity\User\User::getInstance($userId1)
    ->getChatWith($userId2, false);

if (!$chat)
{
    die('Чат не найден');
}

if ($chat->getType() !== 'P')
{
    die('Найден не приватный чат');
}

$chatId = (int)$chat->getChatId();

$result = $chat->deleteChat();

if ($result->isSuccess())
{
    echo 'Чат удалён. CHAT_ID=' . $chatId;
}
else
{
    foreach ($result->getErrors() as $error)
    {
        echo $error->getMessage() . '<br>';
    }
}
```
### Проверить содержимое папки

```php

$base = '/home/bitrix/log/1c';

echo '<pre>';

$iterator = new RecursiveIteratorIterator(
    new RecursiveDirectoryIterator(
        $base,
        FilesystemIterator::SKIP_DOTS
    )
);

foreach ($iterator as $file) {
    $path = $file->getPathname();

    if (stripos($path, 'task') !== false) {
        echo $path . PHP_EOL;
    }
}

echo '</pre>';
```


### Прочесть последние строки лога
```php
$path = '/home/bitrix/log/1c/incoming/absence/create_or_update/error.log';
$count = 1000;

$fp = fopen($path, 'rb');

if (!$fp) {
    echo 'Не удалось открыть файл';
    return;
}

fseek($fp, 0, SEEK_END);
$pos = ftell($fp);

$data = '';
$lines = 0;
$chunkSize = 8192;

while ($pos > 0 && $lines <= $count) {
    $read = min($chunkSize, $pos);
    $pos -= $read;

    fseek($fp, $pos);
    $chunk = fread($fp, $read);

    $data = $chunk . $data;
    $lines = substr_count($data, "\n");
}

fclose($fp);

$rows = preg_split('/\R/', $data);

if (end($rows) === '') {
    array_pop($rows);
}

$rows = array_slice($rows, -$count);

echo '<pre>';
echo htmlspecialchars(implode("\n", $rows));
echo '</pre>';

```