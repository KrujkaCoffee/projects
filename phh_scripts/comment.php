// POWERZ: expanded source-comment experiment, seven confirmed SCRIPT tags in two files.
// Paste into the Bitrix PHP command line WITHOUT opening/closing PHP tags.
// First restore earlier experiments using action=on in their own scripts.
// off = add PHP block comments; on = restore originals; status = read only.
// CSS links remain unchanged. Counters, chat and Bitrix-generated JS are outside this scope.
// Applies to every page using these files, for all visitors. No automatic restore.
$action = 'off';

(static function ($action) {
    global $USER;
    $out = static function ($message) {
        echo htmlspecialchars((string)$message, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8') . "\n";
    };
    $lock = null;
    $staged = [];
    $committed = [];
    $jobs = [];
    echo '<pre>';
    try {
        if (!is_object($USER) || !method_exists($USER, 'IsAdmin') || !$USER->IsAdmin()) {
            throw new RuntimeException('Administrator session required.');
        }
        if (!in_array($action, ['off', 'on', 'status'], true)) {
            throw new RuntimeException('Use off, on or status.');
        }
        $root = realpath($_SERVER['DOCUMENT_ROOT'] ?? '');
        if ($root === false || $root !== '/home/k/kompenz/powerz.co/public_html') {
            throw new RuntimeException('Wrong document root. Run only on powerz.co.');
        }
        $definitions = [
            '/include_powerz/v2/head.php' => [
                'JQUERY' => '<script src="/bitrix/themes/powerz_new-v2/lib/jquery-1.11.1.min.js"></script>',
                'BOOTSTRAP' => '<script src="/bitrix/themes/powerz_new-v2/lib/bootstrap/js/bootstrap.min.js"></script>',
                'FANCYBOX' => '<script src="/bitrix/themes/powerz_new-v2/lib/fancybox/jquery.fancybox.pack.js"></script>',
                'TEMPLATE' => '<script src="/bitrix/themes/powerz_new-v2/js/template.js?v20191126"></script>',
                'CAROUFREDSEL' => '<script src="/bitrix/themes/powerz_new-v2/lib/carouFredSel/jquery.carouFredSel-6.2.1-packed.js"></script>',
                'HTML5SHIV' => '<script src="https://oss.maxcdn.com/libs/html5shiv/3.7.0/html5shiv.js"></script>'
            ],
            '/bitrix/templates/powerz-products-new-v2/header.php' => [
                'FANCYBOX_DUPLICATE' => '<script src="/bitrix/themes/powerz_new-v2/lib/fancybox/jquery.fancybox.pack.js"></script>'
            ]
        ];
        $dir = dirname($root) . '/powerz-script-comments-v2';
        $manifestPath = $dir . '/manifest.json';
        $read = static function ($path) {
            if (is_link($path) || !is_file($path) || !is_readable($path)) {
                throw new RuntimeException('Missing, unreadable or symlink file: ' . $path);
            }
            $data = file_get_contents($path, false, null, 0, 1048577);
            if ($data === false || strlen($data) > 1048576) {
                throw new RuntimeException('Cannot read file within 1 MiB: ' . $path);
            }
            return $data;
        };
        $checkFile = static function ($file) {
            clearstatcache(true, $file);
            $stat = @stat($file);
            if (is_link($file) || realpath($file) !== $file || !is_file($file)
                || $stat === false || $stat['nlink'] !== 1) {
                throw new RuntimeException('Refusing missing, redirected or hard-linked file: ' . $file);
            }
            return $stat;
        };
        $makeOff = static function ($source, $tags) {
            if (!function_exists('token_get_all') || !defined('TOKEN_PARSE')) {
                throw new RuntimeException('PHP tokenizer with TOKEN_PARSE is required.');
            }
            if (preg_match('~<\?(?!php\b|=|xml\b)~i', $source) && !ini_get('short_open_tag')) {
                throw new RuntimeException('Source uses short PHP tags but short_open_tag is disabled.');
            }
            if (strpos($source, 'POWERZ_TEMP_JS_OFF_') !== false
                || strpos($source, 'POWERZ_COMMENT_V2_') !== false) {
                throw new RuntimeException('Existing source-comment experiment. Restore its original first.');
            }
            foreach ($tags as $tag) {
                if (substr_count($source, $tag) !== 1 || strpos($tag, '*/') !== false) {
                    throw new RuntimeException('Expected exactly one unchanged, comment-safe tag: ' . $tag);
                }
            }
            $eol = strpos($source, "\r\n") !== false ? "\r\n" : "\n";
            $counts = array_fill_keys(array_keys($tags), 0);
            $result = '';
            foreach (token_get_all($source, TOKEN_PARSE) as $token) {
                $text = is_array($token) ? $token[1] : $token;
                if (is_array($token) && $token[0] === T_INLINE_HTML) {
                    foreach ($tags as $key => $tag) {
                        $replacement = '<?php /* POWERZ_COMMENT_V2_' . $key . $eol
                            . $tag . $eol . '*/ ?>';
                        $count = 0;
                        $text = str_replace($tag, $replacement, $text, $count);
                        $counts[$key] += $count;
                    }
                }
                $result .= $text;
            }
            foreach ($counts as $count) {
                if ($count !== 1) {
                    throw new RuntimeException('A target is not in plain HTML. Nothing patched.');
                }
            }
            foreach (token_get_all($result, TOKEN_PARSE) as $token) {
                if (is_array($token) && $token[0] === T_INLINE_HTML) {
                    foreach ($tags as $tag) {
                        if (strpos($token[1], $tag) !== false) {
                            throw new RuntimeException('A target remained outside a PHP comment.');
                        }
                    }
                }
            }
            return $result;
        };
        if (is_link($dir) || (file_exists($dir) && realpath($dir) !== $dir)) {
            throw new RuntimeException('Backup directory is redirected.');
        }
        foreach (array_keys($definitions) as $relative) {
            $checkFile($root . $relative);
        }
        if ($action === 'status') {
            foreach ($definitions as $relative => $tags) {
                $source = $read($root . $relative);
                $out('FILE: ' . $relative);
                foreach ($tags as $key => $tag) {
                    $out($key . ': markers=' . substr_count($source, 'POWERZ_COMMENT_V2_' . $key)
                        . '; source occurrences=' . substr_count($source, $tag));
                }
                if (strpos($source, 'POWERZ_TEMP_JS_OFF_') !== false) {
                    $out('OLD TWO-TAG EXPERIMENT STILL PRESENT: restore it with its own action=on.');
                }
            }
            $out('BACKUP MANIFEST: ' . (is_file($manifestPath) ? 'PRESENT' : 'ABSENT'));
            $out('Read only. Source occurrences include comments; check the actual page separately.');
            return;
        }
        if ($action === 'off') {
            foreach (['/bitrix/themes/powerz_new-v2/lib/jquery-1.11.1.min.js',
                      '/bitrix/themes/powerz_new-v2/lib/bootstrap/js/bootstrap.min.js'] as $js) {
                if (!is_file($root . $js) || !is_readable($root . $js)) {
                    throw new RuntimeException('Restore the earlier file-isolation experiment first: ' . $js);
                }
            }
            $index = $read($root . '/index.php');
            if (strpos($index, 'POWERZ_ALL_JS_') !== false) {
                throw new RuntimeException('Restore the HTML-filter experiment with its own action=on first.');
            }
        }
        if (!is_dir($dir)) {
            if ($action !== 'off' || !mkdir($dir, 0700)) {
                throw new RuntimeException('No backup directory available.');
            }
        }
        if (!chmod($dir, 0700) || realpath($dir) !== $dir || is_link($dir . '/.lock')) {
            throw new RuntimeException('Cannot secure the private backup directory.');
        }
        $lock = fopen($dir . '/.lock', 'c');
        if ($lock === false || !flock($lock, LOCK_EX | LOCK_NB)) {
            throw new RuntimeException('Another copy may be running; lock unavailable.');
        }
        $manifest = null;
        if (file_exists($manifestPath) || is_link($manifestPath)) {
            $manifest = json_decode($read($manifestPath), true);
            if (!is_array($manifest) || ($manifest['format'] ?? null) !== 2
                || array_keys($manifest['files'] ?? []) !== array_keys($definitions)) {
                throw new RuntimeException('Unexpected backup manifest. Nothing patched.');
            }
        } elseif ($action === 'on') {
            throw new RuntimeException('No manifest for this experiment. Use the previous script to undo previous changes.');
        }
        $number = 0;
        foreach ($definitions as $relative => $tags) {
            $number++;
            $file = $root . $relative;
            $stat = $checkFile($file);
            $current = $read($file);
            $backup = $dir . '/' . $number . '.original';
            $original = $manifest === null ? $current : $read($backup);
            if ($manifest !== null && (!is_string($manifest['files'][$relative] ?? null)
                || !hash_equals($manifest['files'][$relative], hash('sha256', $original)))) {
                throw new RuntimeException('Backup hash mismatch: ' . $relative);
            }
            $disabled = $makeOff($original, $tags);
            if ($current !== $original && $current !== $disabled) {
                throw new RuntimeException('File differs from both saved states; refusing to overwrite edits: ' . $relative);
            }
            $target = $action === 'off' ? $disabled : $original;
            $jobs[$relative] = compact('file', 'stat', 'current', 'backup', 'original', 'target');
        }
        // All source and syntax checks above finish before any original backup or live-file write.
        $writeNew = static function ($path, $data) use ($read) {
            if (file_exists($path) || is_link($path)) {
                throw new RuntimeException('Refusing to overwrite backup: ' . $path);
            }
            $handle = fopen($path, 'x+b');
            if ($handle === false) { throw new RuntimeException('Cannot create backup: ' . $path); }
            try {
                if (!chmod($path, 0600) || fwrite($handle, $data) !== strlen($data) || !fflush($handle)) {
                    throw new RuntimeException('Incomplete backup: ' . $path);
                }
            } finally { fclose($handle); }
            if ($read($path) !== $data) { throw new RuntimeException('Backup verification failed: ' . $path); }
        };
        if ($manifest === null) {
            $manifest = ['format' => 2, 'files' => []];
            foreach ($jobs as $relative => $job) {
                // Reuse only an exact original if a previous backup-only attempt was interrupted.
                if (file_exists($job['backup']) || is_link($job['backup'])) {
                    if ($read($job['backup']) !== $job['original']) {
                        throw new RuntimeException('Unfinished backup differs from live source: ' . $relative);
                    }
                } else { $writeNew($job['backup'], $job['original']); }
                $manifest['files'][$relative] = hash('sha256', $job['original']);
            }
            $json = json_encode($manifest, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
            if (!is_string($json)) { throw new RuntimeException('Cannot encode backup manifest.'); }
            $writeNew($manifestPath, $json . "\n");
        }
        $stage = static function ($data, $stat) use ($dir, $read, &$staged) {
            $dirStat = stat($dir);
            if ($dirStat === false || $dirStat['dev'] !== $stat['dev']) {
                throw new RuntimeException('Atomic replacement requires the same filesystem.');
            }
            $path = tempnam($dir, 'stage-');
            if ($path === false) { throw new RuntimeException('Cannot stage replacement.'); }
            $staged[] = $path;
            if (realpath(dirname($path)) !== $dir
                || file_put_contents($path, $data, LOCK_EX) !== strlen($data) || $read($path) !== $data) {
                throw new RuntimeException('Staged file verification failed.');
            }
            if ((fileowner($path) !== $stat['uid'] && !@chown($path, $stat['uid']))
                || (filegroup($path) !== $stat['gid'] && !@chgrp($path, $stat['gid']))
                || !chmod($path, $stat['mode'] & 0777)) {
                throw new RuntimeException('Cannot preserve file ownership or permissions.');
            }
            return $path;
        };
        foreach ($jobs as $relative => $job) {
            if ($job['current'] !== $job['target']) {
                $jobs[$relative]['stage'] = $stage($job['target'], $job['stat']);
                $jobs[$relative]['rollback'] = $stage($job['current'], $job['stat']);
            }
        }
        foreach ($jobs as $relative => $job) {
            $checkFile($job['file']);
            if ($read($job['file']) !== $job['current']) {
                throw new RuntimeException('File changed during preparation: ' . $relative);
            }
        }
        foreach ($jobs as $relative => $job) {
            if (!isset($job['stage'])) { continue; }
            $checkFile($job['file']);
            if ($read($job['file']) !== $job['current'] || !rename($job['stage'], $job['file'])) {
                throw new RuntimeException('Concurrent edit or replacement failure: ' . $relative);
            }
            $committed[] = $relative;
            clearstatcache(true, $job['file']);
            if (function_exists('opcache_invalidate')) { @opcache_invalidate($job['file'], true); }
            if ($read($job['file']) !== $job['target']) {
                throw new RuntimeException('Post-write check failed: ' . $relative);
            }
        }
        $out(strtoupper($action) . ': OK. ' . ($action === 'off'
            ? 'All seven confirmed SCRIPT tags are inside PHP comments.' : 'Both original source files restored.'));
        foreach ($jobs as $relative => $job) { $out('FILE: ' . $relative); }
        $out('BACKUPS: ' . $dir);
        $out('Scope: six tags in head.php plus one duplicate Fancybox in the product header.');
        $out('Other script sources are not covered. This is not a full-site JavaScript shutdown.');
        $out('No page/CDN cache clearing. Verify fresh page HTML before repeating the same URL scan.');
        $out('Use action=on in THIS script to restore these two files. No automatic restore.');
    } catch (Throwable $error) {
        $out('STOP: ' . $error->getMessage());
        foreach (array_reverse($committed) as $relative) {
            $job = $jobs[$relative];
            try {
                $checkFile($job['file']);
                if ($read($job['file']) !== $job['target'] || !rename($job['rollback'], $job['file'])) {
                    throw new RuntimeException('Concurrent edit or restore failure.');
                }
                clearstatcache(true, $job['file']);
                if (function_exists('opcache_invalidate')) { @opcache_invalidate($job['file'], true); }
                if ($read($job['file']) !== $job['current']) { throw new RuntimeException('Restore verification failed.'); }
                $out('ROLLED BACK: ' . $relative);
            } catch (Throwable $restoreError) {
                $out('RESTORE NOT CONFIRMED: ' . $relative . '; original backup: ' . $job['backup']);
            }
        }
        if (!$committed) { $out('No live source files changed.'); }
    } finally {
        foreach ($staged as $path) { if (is_file($path)) { @unlink($path); } }
        if (is_resource($lock)) { flock($lock, LOCK_UN); fclose($lock); }
        echo '</pre>';
    }
})($action);