<?

use Bitrix\Main\Diag\Debug;

require_once('const.php');
spl_autoload_register(function ($class) {
  if(strpos($class, 'FL') !== false){
    $path = explode('\\', $class);
    unset($path[0]);
    include_once(\Bitrix\Main\Application::getDocumentRoot() . '/local/lib/fl/' . implode('/', $path) . '.php');
  }
});


//\Bitrix\Main\EventManager::getInstance()->addEventHandler('iblock', 'OnAfterIBlockElementUpdate', ['HandlersCatcher', 'OnAfterIBlockElementUpdateHandler']);
//\Bitrix\Main\EventManager::getInstance()->addEventHandler('main', 'OnAfterUserUpdate', ['HandlersCatcher', 'OnAfterUserUpdateHandler']);
//\Bitrix\Main\EventManager::getInstance()->addEventHandler('rest', 'OnRestServiceBuildDescription', ['HandlersCatcher', 'OnRestServiceBuildDescription']);

class HandlersCatcher {

  function OnRestServiceBuildDescription() {
    return [
      'kekwtask' => [
        'kekwtask.add' => [
          'callback' => ['\FL\Rest\Task', 'add'],
          'options' => [],
        ],
      ]
    ];
  }

  function OnAfterIBlockElementUpdateHandler(&$arFields) {
    //error_log('Обновление инфоблока'."\n", 3, $_SERVER['DOCUMENT_ROOT'].'/log.txt');
    //error_log(var_export($arFields, true)."\n", 3, $_SERVER['DOCUMENT_ROOT'].'/log.txt');
    if ($arFields['IBLOCK_ID'] == IBLOCK_IDS['SOTRUDNIKI']) {
      if ($arFields['RESULT']) {
        $userId = reset($arFields['PROPERTY_VALUES'][IBLOCK_PROPERTIES['ID_SOTRUDNIKA']])['VALUE'];
        if ($userId) {
          $cUser = new CUser;
          $fields = [];

          if (isset(reset($arFields['PROPERTY_VALUES'][IBLOCK_PROPERTIES['WORK_PHONE']])['VALUE'])) {
            $fields['WORK_PHONE'] = reset($arFields['PROPERTY_VALUES'][IBLOCK_PROPERTIES['WORK_PHONE']])['VALUE'];
          }
          if (isset(reset($arFields['PROPERTY_VALUES'][IBLOCK_PROPERTIES['INNER_PHONE']])['VALUE'])) {
            $fields['UF_PHONE_INNER'] = reset($arFields['PROPERTY_VALUES'][IBLOCK_PROPERTIES['INNER_PHONE']])['VALUE'];
          }
          if (isset(reset($arFields['PROPERTY_VALUES'][IBLOCK_PROPERTIES['PERSONAL_PHONE']])['VALUE'])) {
            $fields['PERSONAL_MOBILE'] = reset($arFields['PROPERTY_VALUES'][IBLOCK_PROPERTIES['PERSONAL_PHONE']])['VALUE'];
          }

          if ($fields) {
            $cUser->Update($userId, $fields);
          }
        }
      }
    }
  }

  function OnAfterUserUpdateHandler(&$arFields) {
    //error_log('Обновление пользователя'."\n", 3, $_SERVER['DOCUMENT_ROOT'].'/log.txt');
    //error_log(var_export($arFields, true)."\n", 3, $_SERVER['DOCUMENT_ROOT'].'/log.txt');
    if ($arFields['RESULT']) {
      $el = new CIBlockElement;
      $res = $el->GetList([], ['IBLOCK_ID' => IBLOCK_IDS['SOTRUDNIKI'], 'PROPERTY_ID_SOTRUDNIKA' => $arFields['ID']], false, false, ['ID', 'IBLOCK_ID', 'PROPERTY_ID_SOTRUDNIKA']);
      if ($user = $res->Fetch()) {
        $props = [];

        if (isset($arFields['WORK_PHONE'])) {
          $props[IBLOCK_PROPERTIES['WORK_PHONE']] = $arFields['WORK_PHONE'];
        }
        if (isset($arFields['UF_PHONE_INNER'])) {
          $props[IBLOCK_PROPERTIES['INNER_PHONE']] = $arFields['UF_PHONE_INNER'];
        }
        if (isset($arFields['PERSONAL_MOBILE'])) {
          $props[IBLOCK_PROPERTIES['PERSONAL_PHONE']] = $arFields['PERSONAL_MOBILE'];
        }

        if ($props) {
          $el->SetPropertyValuesEx($user['ID'], IBLOCK_IDS['SOTRUDNIKI'], $props);
          CIBlock::clearIblockTagCache(IBLOCK_IDS['SOTRUDNIKI']);
        }
      }
    }
  }

}
\FL\Handlers\Event::init();



require_once('/home/bitrix/lib/vendor/autoload.php');

require_once dirname(__FILE__) . '/event_handler.php';

function custom_mail($to, $subject, $message, $additional_headers, $additional_parameters){
    return \Kuratovru\Mail\Mailer::customMail($to, $subject, $message, $additional_headers, $additional_parameters);
}


//TODO Заготовка для мобильного приложения
/*AddEventHandler("mobile", "onMobileMenuStructureBuilt", Array("CStudiobitEvents", "onMobileMenuStructureBuilt"));

class CStudiobitEvents
{
    public function onMobileMenuStructureBuilt($menu)
    {
        $menu[] = array(
            'title' => 'Другое',
            'min_api_version' => 22,
            'hidden' => false,
            'sort' => 22,
            'items' =>
                array(
                    array(
                        'title' => 'Компания',
                        'color' => '#8bd100',
                        'unselectable' => true,
                        'imageUrl' => '',
                        'attrs' =>
                            array (
                                'url' => '/mobile/about/',
                                'id' => 'company_about',
                            ),
                    ),
                )
        );

        return $menu;
    }
}*/


//TODO агенты для файлооборота

function getAndDeleteOldChatsFiles(){

    \Bitrix\Main\Loader::IncludeModule( 'disk' );
    \Bitrix\Main\Loader::IncludeModule( 'im' );
    \Bitrix\Main\Loader::IncludeModule('tasks');
    \Bitrix\Main\Loader::IncludeModule('forum');

    $date = new \DateTime('now');
    $date->modify('-28 day');
    $date = ConvertTimeStamp($date->getTimestamp(), 'FULL');

    $chats = \Bitrix\Im\Model\ChatTable::getList([
        'select' => ['ID', 'DISK_FOLDER_ID'],
        'filter' => ['!DISK_FOLDER_ID' => ''],
    ])->fetchAll();

    $data = [];
    foreach ( $chats as $chat ):
        $objects = Bitrix\Disk\Internals\ObjectTable::getList([
            'select' => ['FILE_ID'],
            'filter' => ['PARENT_ID' => $chat['DISK_FOLDER_ID'], '<CREATE_TIME' => $date, '!FILE_ID' => '']
        ])->fetchAll();

        $data = array_merge($data, array_map(function($item){
            return $item['FILE_ID'];
        }, $objects));
    endforeach;


    foreach ( $data as $id ):
        if ( $id ):
            $diskFile  = \Bitrix\Disk\File::load([
                '=FILE_ID'  =>  $id
            ]);

            $diskFile->delete(1);
        endif;
    endforeach;

    return 'getAndDeleteOldChatsFiles();';
}

//Вставка telegram в шапку
\Bitrix\Main\Page\Asset::getInstance()->addJs("/local/templates/.default/js/telegram.js");