<?php
use Bitrix\Main;

use \Bitrix\Recyclebin;

$eventManager = Main\EventManager::getInstance();

//Добавляем кастомное поле Текст-Список
$eventManager->addEventHandler('main', 'OnUserTypeBuildList', ['Kuratovru\UserFieldTypes\StringEnum', 'GetUserTypeDescription']);

//Добавляем фикс для докуметов
$eventManager->addEventHandler('documentgenerator', 'onBeforeProcessDocument', ['Kuratovru\CRM\DocumentGeneratorModification', 'process']);

//Блокировка диска
//$eventManager->addEventHandler("main", "OnBeforeProlog", ['Kuratovru\Disk\DiskBlocker', 'blockDisk']);

//Скрытая корзина
$eventManager->addEventHandler("recyclebin", "onElementDelete", ['Kuratovru\Util\TaskTrash', 'process']);

//Добавление уведомления о входящей почте для со-ответственных
//$eventManager->addEventHandler("crm", "OnAfterCrmAddEvent", ['Kuratovru\CRM\EntityEmailHandler', 'process']);

//При создании и изменении сделки проверияем, есть ли права на клиента у пользователя
//$eventManager->addEventHandler("crm", "OnBeforeCrmDealAdd", ['Kuratovru\CRM\DealPermissionHandler', 'processAdd']);
//$eventManager->addEventHandler("crm", "OnBeforeCrmDealUpdate", ['Kuratovru\CRM\DealPermissionHandler', 'processUpdate']);

//Рассылаем уведы после прохождения теста все причастным
$eventManager->addEventHandler("learning", "OnAfterAttemptFinished", ['Kuratovru\Learning\LearningEvents', 'sendNotify']);

//Отправка задач на Администратора портала в Планфикс
//$eventManager->addEventHandler("tasks", "OnTaskAdd", ['Kuratovru\Rest\Planfix', 'sendTask']);

//Заметное уведомление о сообщении в чат
$eventManager->addEventHandler("imconnector", "OnReceivedMessage", ['Kuratovru\Util\ChatNotification', 'OnReceivedMessage']);

//Отслеживание завершения задач для планов адаптации
$eventManager->addEventHandler("tasks", "OnBeforeTaskUpdate", ['Kuratovru\Util\Adaptation', 'handleTask']);

//Отслеживание завершения задач для планов вторичной адаптации
$eventManager->addEventHandler("tasks", "OnBeforeTaskUpdate", ['Kuratovru\Util\Adaptation', 'handleSecondTask']);

//Отслеживание деактивации пользователя для поддержания
$eventManager->addEventHandler("main", "OnBeforeUserUpdate", ['Kuratovru\Util\WorkaroundSheets', 'handleUserDeactivation']);

//Удаление всех файлов и вложений по завершению задачи
//$eventManager->addEventHandler("tasks", "OnTaskUpdate", ['Kuratovru\Util\Util', 'deleteTaskAttachments']);

//Логирование авторизаций пользователей
$eventManager->addEventHandler("main", "OnUserLogin", ['Kuratovru\Util\UserLogin', 'handleOnUserLogin']);
$eventManager->addEventHandler("main", "OnBeforeUserLogout", ['Kuratovru\Util\UserLogin', 'handleOnBeforeUserLogout']);


$eventManager->addEventHandler('Bitrix\Tasks\Access\TaskAccessController', \Bitrix\Main\Access\Event\EventDictionary::EVENT_ON_AFTER_CHECK, 'taskChangeResponsible');

function taskChangeResponsible($event){

    $params = $event->getParameters();

    if (
        $params['action'] === \Bitrix\Tasks\Access\ActionDictionary::ACTION_TASK_CHANGE_ACCOMPLICES &&
        !empty($params['params'])
        && $params['isAccess'] == 0
    ):

        $userId = $params['user']->getUserId();
        $accomplices = $params['params']->getMembers()['A'];

        $userIsHead = false;
        $dbRes = CIBlockSection::GetList(
            [],
            [
                'IBLOCK_ID' => COption::GetOptionInt('intranet', 'iblock_structure'),
                'UF_HEAD' => $userId,
            ],
            false
        );

        if ( $dbRes->Fetch())
            $userIsHead = true;


        $accomplicesIsHeads = true;
        foreach ( $accomplices as $accomplice ):
            $dbRes = CIBlockSection::GetList(
                [],
                [
                    'IBLOCK_ID' => COption::GetOptionInt('intranet', 'iblock_structure'),
                    'UF_HEAD' => $accomplice,
                ],
                false
            );

            if ( !$dbRes->Fetch())
                $accomplicesIsHeads = false;

        endforeach;

        //Сценарий Начальник А ставит в соисполнители Начальников отделов
        if ( $accomplicesIsHeads && $userIsHead ):
            $result = new \Bitrix\Main\Access\Event\EventResult(\Bitrix\Main\Access\Event\EventResult::SUCCESS);
            $result->allowAccess();
            return $result;
        endif;

        /*
        $userId = $params['user']->getUserId();
        $responsible = $params['params']->getMembers()['R'][0];

        $userIsHead = false;
        $dbRes = CIBlockSection::GetList(
            [],
            [
                'IBLOCK_ID' => COption::GetOptionInt('intranet', 'iblock_structure'),
                'UF_HEAD' => $userId,
            ],
            false
        );

        if ( $dbRes->Fetch())
            $userIsHead = true;

        $responsibleIsHead = false;
        $dbRes = CIBlockSection::GetList(
            [],
            [
                'IBLOCK_ID' => COption::GetOptionInt('intranet', 'iblock_structure'),
                'UF_HEAD' => $responsible,
            ],
            false
        );


        if ( $dbRes->Fetch())
            $responsibleIsHead = true;

        //Сценарий Начальник А - Начальнику Б
        if ( $responsibleIsHead && $userIsHead ):
            $result = new \Bitrix\Main\Access\Event\EventResult(\Bitrix\Main\Access\Event\EventResult::SUCCESS);
            $result->allowAccess();
            return $result;
        endif;

        $userSubOrdinate = new \Bitrix\Main\Access\User\UserSubordinate($userId);

        //Сценарий Начальник Б - Сотруднику Б
        if ( $userIsHead && $userSubOrdinate->getSubordinate($responsible) === \Bitrix\Main\Access\User\UserSubordinate::RELATION_SUBORDINATE ):
            $result = new \Bitrix\Main\Access\Event\EventResult(\Bitrix\Main\Access\Event\EventResult::SUCCESS);
            $result->allowAccess();
            return $result;
        endif;
        */

//

        /*file_put_contents('/home/bitrix/log/info/log2.txt', print_r([
            'user' => $user->getUserId(),
            'members' => $responsible
        ],true). PHP_EOL, FILE_APPEND);*/
    endif;


}

//Инициировать глобальные константы
\Kuratovru\V2\Utils\Globals::init();

//Обработка событий лидов
\Kuratovru\V2\CRM\Lead::handleEvents();

//Обработка событий контактов
\Kuratovru\V2\CRM\Contact::handleEvents();

//Обработка событий компаний
\Kuratovru\V2\CRM\Company::handleEvents();

//Обработка событий сделок
\Kuratovru\V2\CRM\Deal::handleEvents();

//Обработка событий активных уведомлений
\Kuratovru\V2\Im\Notifications::handleEvents();

//Добавление точки входа REST API для работы с пользователями
$eventManager->addEventHandler('rest', 'OnRestServiceBuildDescription', ['Kuratovru\V2\Rest\User', 'handler']);

//Добавление точки входа REST API для работы с подразделениями
$eventManager->addEventHandler('rest', 'OnRestServiceBuildDescription', ['Kuratovru\V2\Rest\Department', 'handler']);

//Добавление точки входа REST API для работы с уведомлениями об ошибках обмена
$eventManager->addEventHandler('rest', 'OnRestServiceBuildDescription', ['Kuratovru\V2\Rest\Notification', 'handler']);

//Добавление точки входа REST API для работы с компаниями
$eventManager->addEventHandler('rest', 'OnRestServiceBuildDescription', ['Kuratovru\V2\Rest\Company', 'handler']);

//Добавление точки входа REST API для работы с контактами
$eventManager->addEventHandler('rest', 'OnRestServiceBuildDescription', ['Kuratovru\V2\Rest\Contact', 'handler']);

//Добавление точки входа REST API для работы со сделками
$eventManager->addEventHandler('rest', 'OnRestServiceBuildDescription', ['Kuratovru\V2\Rest\Deal', 'handler']);

$eventManager->addEventHandler('rest', 'OnRestServiceBuildDescription', ['Kuratovru\V2\Rest\Absence', 'handler']);

//Функционал отключен, т.к. не учитывает особенностей обмена отсутствиями (цикл полного удаления - полного добавления)
/*$eventManager->addEventHandler('iblock', 'OnAfterIBlockElementAdd', ['Kuratovru\V2\Bizproc\Absence', 'handlerAdd']);

$eventManager->addEventHandler('iblock', 'OnAfterIBlockElementDelete', ['Kuratovru\V2\Bizproc\Absence', 'handlerDelete']);*/

//Подключить кастомные JS-скрипты
\Kuratovru\V2\Assets\Assets::run();

//Отслеживание запросов на изменение Активити владельцем-наблюдателем Активити
\Kuratovru\V2\CRM\Activity::handleActivityObserverAction();

//Отслеживание запросов на создание Дела-письма для автоматической передачи ответственности
$eventManager->addEventHandler('crm', 'OnActivityAdd', ['Kuratovru\V2\CRM\Activity', 'autoChangeResponsibleOnMailActivity']);

//Отслеживание запросов на создание входящего Дела-звонка для автоматического завершения
$eventManager->addEventHandler('crm', 'OnActivityAdd', ['Kuratovru\V2\CRM\Activity', 'autoCompleteCallActivity']);

//Отслеживание запросов на экспорт данных CRM для удаления контактных данных из выгрузки
$eventManager->addEventHandler('main', 'OnBeforeProlog', ["\Kuratovru\V2\CRM\Export", "preserveExportContactData"], );

//Блокировка запросов из мобильного приложения
$eventManager->addEventHandler('main', 'OnBeforeProlog', ["\Kuratovru\V2\Mobile\MobileAccessChecker", 'onBeforeProlog']);