<?php

if(!defined("B_PROLOG_INCLUDED") || B_PROLOG_INCLUDED !== true) die();

use Kuratovru\Model\Service\Service;

use Bitrix\Main\Engine\ActionFilter\Authentication;
use Bitrix\Main\Error;
use Bitrix\Main\ErrorCollection;
use Kuratovru\Model\TaskBuilder\TaskServiceBuilder;

use Bitrix\Main\Page\Asset;

class ServicesMain extends \CBitrixComponent implements \Bitrix\Main\Engine\Contract\Controllerable, \Bitrix\Main\Errorable{

    private $departmentIdblockId = 55;

    protected $extraFieldsConfig = [];

    public function __construct($component = null){
        parent::__construct($component);

        $this->fillExtraFields();
    }

    private function getProjectsForProjectPicker(){
        global $USER;

        //Получаем список открытых и активных проектов
        \Bitrix\Main\Loader::includeModule("socialnetwork");

        $groupsResult = \CSocNetGroup::GetList(['ID' => 'DESC'], [
            'ACTIVE' => 'Y',
            'OPENED' => 'Y',
            'CHECK_PERMISSIONS' => $USER->getId(),
        ], false, false, ['ID', 'NAME']);

        $projects = [];

        while ($group = $groupsResult->fetch()):
            $projects[] = [
                'id' => $group['ID'],
                'title' => $group['NAME'],
                'entityId' => 'projectCustom',
                'tabs' => 'projectsCustom'
            ];
        endwhile;

        return $projects;
    }

    private function getElementsForIB($iblockId){
        global $USER;

        //Получаем список активных элементов IB
        \Bitrix\Main\Loader::includeModule("iblock");

        $elements = [];

        $results = \CIBlockElement::GetList([], ['ACTIVE' => 'Y', 'IBLOCK_ID' => $iblockId], false, false, ['ID', 'NAME']);
        while($result = $results->fetch()):
            $elements[] = [
                'label' => $result['NAME'],
                'value' => $result['NAME'],
            ];
        endwhile;

        return $elements;
    }

    private function fillExtraFields(){
        $this->extraFieldsConfig = include 'config.php';


        $projects = [];
        $ib_elements = [];
        foreach ( $this->extraFieldsConfig['sections'] as &$section ):
            foreach ( $section['fields'] as &$field ):
                //Записываем открытые проекты для projectpicker-полей
                if ( $field['type'] === 'projectpicker' ):
                    if (!$projects):
                        $projects = $this->getProjectsForProjectPicker();
                    endif;
                    $field['values'] = $projects;
                endif;
                unset($projects);

                //Записываем элементы ИБ для iblock_elements
                if ( $field['type'] === 'iblock_elements' ):
                    if (!$ib_elements):
                        $ib_elements = $this->getElementsForIB($field['iblock_id']);
                    endif;
                    $field['values'] = $ib_elements;
                endif;
                unset($ib_elements);
            endforeach;
            unset($field);
        endforeach;
        unset($section);

        foreach ( $this->extraFieldsConfig['elements'] as &$element ):
            foreach ( $element['fields'] as &$field ):
                //Записываем открытые проекты для projectpicker-полей
                if ( $field['type'] === 'projectpicker' ):
                    if (!$projects):
                        $projects = $this->getProjectsForProjectPicker();
                    endif;
                    $field['values'] = $projects;
                endif;
                unset($projects);

                //Записываем элементы ИБ для iblock_elements
                if ( $field['type'] === 'iblock_elements' ):
                    if (!$ib_elements):
                        $ib_elements = $this->getElementsForIB($field['iblock_id']);
                    endif;
                    $field['values'] = $ib_elements;
                endif;
                unset($ib_elements);
            endforeach;
            unset($field);
        endforeach;
        unset($element);
    }

    private function getResponsibleDepartments( int $parentId = 0 ) : array {
        $departments = [];

        $results = Service::getChildSections($parentId);

        foreach ($results as $result):
            $departments[] = [
                'label' => $result['NAME'],
                'value' => $result['ID']
            ];
        endforeach;

        return $departments;
    }

    protected function parseFiles($files){
        $data = [];

        for ( $i = 0; $i < count($files['name']); $i++ ):
            $data[] = [
                'error' => $files['error'][$i],
                'name' => $files['name'][$i],
                'size' => $files['size'][$i],
                'tmp_name' => $files['tmp_name'][$i],
                'type' => $files['type'][$i],
            ];
        endfor;

        return $data;
    }

    public function getPrioritiesList() : string{
        $priorities = [
            [
                'label' => 'Низкий приоритет',
                'value' => '95',
            ],
            [
                'label' => 'Важно',
                'value' => '96',
            ],
            [
                'label' => 'Критично',
                'value' => '97',
            ]
        ];
        return \CUtil::PhpToJSObject($priorities);
    }

    public function getDepartmentsList() : string{
        $departments = [];

        $results = \Kuratovru\Helpers\Helper::getDataFromIblock([], [
            'IBLOCK_ID' => $this->departmentIdblockId,
            'ACTIVE' => 'Y'
        ], [
            'ID',
            'NAME'
        ]);

        foreach ($results as $result):
            $departments[] = [
                'label' => $result['NAME'],
                'value' => $result['ID']
            ];
        endforeach;

        return \CUtil::PhpToJSObject($departments);
    }

    public function executeComponent(){

        \Bitrix\Main\UI\Extension::load('ui.entity-selector');

        Asset::getInstance()->addCss("/local/templates/.default/assets/css/flatpickr.min.css");
        Asset::getInstance()->addJs("/local/templates/.default/assets/js/flatpickr.min.js");
        Asset::getInstance()->addJs("/local/templates/.default/assets/js/l10n/ru.js");


        $this->arResult['priorities'] = $this->getPrioritiesList();
        $this->arResult['departments'] = $this->getDepartmentsList();
        $this->arResult['responsible-departments'] = $this->getResponsibleDepartments();
        $this->arResult['extraFieldsConfig'] = \CUtil::PhpToJSObject($this->extraFieldsConfig);

        //\Bitrix\Iblock\Elements\ElementKelastServiceTable::getEntity()->cleanCache();

        $this->includeComponentTemplate();
    }

    public function sendAction() : array{
        $request = Bitrix\Main\Application::getInstance()->getContext()->getRequest();

        $department = $request->getPost("select-department");
        $priority = $request->getPost("select-priority");
        $service = $request->getPost("select-service");
        $deadline = $request->getPost("input-deadline");
        $fieldsForConcatTitle = explode(",", $request->getPost("fields-for-concat-title"));

        $description = $request->getPost("description");

        $customProject = $request->getPost("projectpickerField") ? $request->getPost($request->getPost("projectpickerField")) : false;

        if ( $service ==  240637){
            $department = '-';
            $priority = '-';
            $deadline = (new DateTime())->setTimestamp(time() + 3600);
        }else{
            if ( !$department || !$priority || !$service || !$deadline )
                throw new \RuntimeException();

            $deadline = new DateTime($deadline);
        }

        $fileField = $this->parseFiles($request->getFile('task_files'));

        if ($fileField):

            \Bitrix\Main\Loader::includeModule('disk');

            $driver = \Bitrix\Disk\Driver::getInstance();
            $storage = $driver->getStorageByCommonId('shared_files_s1');

            $folder = $storage->getChild(
                array(
                    '=NAME' => 'Файлы тикетов техподдержки',
                    'TYPE' => \Bitrix\Disk\Internals\FolderTable::TYPE_FOLDER
                )
            );

            $filesArr = [];
            foreach ( $fileField as $fileRow ):

                if ( !empty($fileRow['tmp_name']) ):
                    if ( $fileRow['error'] !== 0):
                        throw new \RuntimeException("Не удалось загрузить файл \"{$fileRow['name']}\"! Попробуйте изменить формат файла!");
                    endif;

                    if ( $fileRow['size'] > 10000000 ):
                        throw new \RuntimeException("Файл \"{$fileRow['name']}\" превышает лимит 10мб! Попробуйте изменить размер файла!");
                    endif;

                    $file = $folder->uploadFile($fileRow, [
                        'CREATED_BY' => \Bitrix\Main\Engine\CurrentUser::get()->getId(),
                        'NAME' => pathinfo($fileRow['name'], PATHINFO_FILENAME) . ' ' . uniqid() . '.' . pathinfo($fileRow['name'], PATHINFO_EXTENSION)
                    ]);

                    $filesArr[] = $file->getId();
                endif;
            endforeach;
        endif;

        $userId = \Bitrix\Main\Engine\CurrentUser::get()->getId();

        $builder = new TaskServiceBuilder($service);

        $departmentService = Service::getById($service)['IBLOCK_SECTION_ID'];

        $builder
            ->setDepartment($department)
            ->setPriority($priority)
            ->setDeadLine($deadline)
            ->setDepartmentService($departmentService)
            ->setDescription($description)
            ->setCreatedBy($userId);

        //Для заявок претензий - постановщик = исполнитель
        if ($service == 255167 || $service == 255216):
            $builder->setResponsible($userId);
        endif;

        foreach ( $filesArr as $fileId ):
            $builder->addFile($fileId);
        endforeach;

        //Другая группа для услуг продвижения сайтов
        if ($service == 244002):
            $builder->setWorkGroup(124);
        endif;

        //Другая группа, если выбрано поле типа projectpicker
        if ( $customProject ):
            $builder->setWorkGroup($customProject);
        endif;

        if (!empty($fieldsForConcatTitle)) {
            $texts = [];

            foreach ($fieldsForConcatTitle as $field) {
                $text = $request->getPost($field);

                if (!empty($text)) {
                    $texts[] = $text;
                }
            }

            // Конкатинирование дополнительного текста к заголовку
            $builder = $this->taskTitleConcat($builder, $texts);
        }

        $taskId = $builder->build()->getTaskId();

        return [
            'userId' => $userId,
            'taskId' => $taskId
        ];
    }

    public function selectAction( int $department = 0 ) : array{

        if ( empty($department) )
            throw new \RuntimeException();

        $result = [];

        $sections = Service::getChildSections($department);

        if ( $sections ):
            $result['type'] = 'department';
            $result['depth'] = $sections[0]['DEPTH_LEVEL'];
            foreach ( $sections as $section ):
                $result['departments'][] = [
                    'label' => $section['NAME'],
                    'value' => $section['ID']
                ];
            endforeach;
        else:
            $result['type'] = 'service';
            $result['services'] = [];

            $services = Service::getBySectionId($department);
            foreach ($services as $service):
                $result['services'][] = [
                    'label' => $service['NAME'],
                    'value' => $service['ID'],
                    'description' => $service['PREVIEW_TEXT'],
                    'leadTime' => FL\Util\Util::getSecondFromServiceFormat($service['LEAD_TIME']),
                    'timeAt' => $service['TIME_AT'],
                    'timeTo' => $service['TIME_TO'],
                    'deadline' => Service::buildDeadline($service['ID'])->getTimestamp(),
                    'startText' => $service['START_TEXT']
                ];
            endforeach;

        endif;

        return $result;
    }

    public function onPrepareComponentParams($arParams){
        $this->errorCollection = new ErrorCollection();
        return $arParams;
    }

    public function configureActions(){
        return [
            'send' => [
                '-prefilters' => [
                    Authentication::class,
                ],
            ],
        ];
    }

    // Метод для конкатинирования дополнительного текста к заголовку задачи
    private function taskTitleConcat(TaskServiceBuilder $task, array $texts): TaskServiceBuilder {
        if (empty($texts)) return $task;

        $title = $task->getTitle();

        foreach ($texts as $text) {
            $title .= '_' . $text;
        }

        $task->setTitle($title);

        return $task;
    }

    /**
     * Getting array of errors.
     * @return Error[]
     */
    public function getErrors()
    {
        return $this->errorCollection->toArray();
    }

    /**
     * Getting once error with the necessary code.
     * @param string $code Code of error.
     * @return Error
     */
    public function getErrorByCode($code)
    {
        return $this->errorCollection->getErrorByCode($code);
    }
}