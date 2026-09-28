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

    // Новые поля снабжения: конфигурация общая для формы и серверной проверки.
    private $serviceRequirements = [];
    private $serviceRequirementIds = [];
    private $serviceRequirementGroups = [];

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
        $this->extraFieldsConfig = include __DIR__ . '/config.php';
        $this->fillServiceRequirements();


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

    /**
     * Дополняет штатный config.php новыми полями, не меняя старые определения.
     * Один и тот же список ID используется при отображении и отправке.
     */
    private function fillServiceRequirements()
    {
        $this->serviceRequirements = require __DIR__ . '/service_requirements.php';
        $environment = (string)($_SERVER['APP_ENV'] ?? '');
        $settings = $this->serviceRequirements['environments'][$environment] ?? [];

        if (empty($settings['enabled'])) {
            return;
        }

        $ids = $settings['service_ids'] ?? [];
        if (!empty($settings['include_ved'])) {
            $ids = array_merge($ids, $settings['ved_service_ids'] ?? []);
        }
        $this->serviceRequirementIds = array_values(array_unique(array_map('intval', $ids)));
        if (!$this->serviceRequirementIds) {
            return;
        }

        // Только новые поля собираются в описание на сервере.
        $decorate = static function (array $fields): array {
            foreach ($fields as &$field) {
                $field['server_description'] = true;
            }
            unset($field);
            return $fields;
        };

        $this->serviceRequirementGroups[] = [
            'values' => $this->serviceRequirementIds,
            'fields' => $decorate($this->serviceRequirements['fields']),
        ];
        $outsourceIds = array_values(array_intersect(
            $this->serviceRequirementIds,
            array_map('intval', $settings['outsource_service_ids'] ?? [])
        ));
        if ($outsourceIds) {
            $this->serviceRequirementGroups[] = [
                'values' => $outsourceIds,
                'fields' => $decorate($this->serviceRequirements['outsource_fields']),
            ];
        }

        $this->extraFieldsConfig['elements'] = array_merge(
            $this->extraFieldsConfig['elements'],
            $this->serviceRequirementGroups
        );
        $this->extraFieldsConfig['serviceRequirements'] = [
            'version' => $this->serviceRequirements['version'],
        ];
    }

    /** Пробелы, переносы и неразрывные/нулевой ширины пробелы не считаются вводом. */
    private function normalizeRequirementValue($value)
    {
        if (!is_string($value)) {
            return null;
        }
        return preg_replace(
            '/\A[\s\p{Z}\x{FEFF}\x{200B}]+|[\s\p{Z}\x{FEFF}\x{200B}]+\z/u',
            '',
            $value
        );
    }

    /**
     * Проверяет ТОЛЬКО новые поля и дополняет описание.
     * Не обращается к построителю, не загружает файлы и не создаёт задачу.
     * Возвращает ошибки отдельным массивом для обработчика формы.
     */
    private function prepareServiceRequirementDescription($serviceId, $description, $request): array
    {
        $result = ['description' => $description, 'errors' => []];
        if (!in_array((int)$serviceId, $this->serviceRequirementIds, true)) {
            // После отключения/изменения охвата не теряем данные открытой ранее формы молча.
            $knownFields = array_merge(
                $this->serviceRequirements['fields'] ?? [],
                $this->serviceRequirements['outsource_fields'] ?? []
            );
            foreach ($knownFields as $field) {
                if ($request->getPost($field['name']) !== null) {
                    $result['errors'][] = 'Настройка услуги изменилась. Сохраните введённые сведения и обновите страницу перед отправкой.';
                    break;
                }
            }
            return $result;
        }

        if ($request->getPost('service_requirements_version') !== $this->serviceRequirements['version']) {
            $result['errors'][] = 'Форма услуг обновилась. Сохраните введённый текст и обновите страницу, затем заполните обязательные поля.';
            return $result;
        }
        if ($description === null) {
            $description = '';
        }
        if (!is_string($description)) {
            $result['errors'][] = 'Некорректное описание заявки.';
            return $result;
        }

        $lines = [];
        foreach ($this->serviceRequirementGroups as $group) {
            if (!in_array((int)$serviceId, $group['values'], true)) {
                continue;
            }
            foreach ($group['fields'] as $field) {
                // Проверяем условие на сервере, а не доверяем скрытию поля в HTML.
                if (!empty($field['visible_if'])) {
                    $condition = $field['visible_if'];
                    $source = $this->normalizeRequirementValue($request->getPost($condition['field']));
                    if ($source !== (string)$condition['equals']) {
                        continue;
                    }
                }

                $raw = $request->getPost($field['name']);
                $value = $raw === null ? '' : $this->normalizeRequirementValue($raw);
                if ($value === null) {
                    $result['errors'][] = 'Некорректное значение поля «' . $field['label'] . '».';
                    continue;
                }
                if ($value === '') {
                    if (!empty($field['required'])) {
                        $result['errors'][] = 'Заполните поле «' . $field['label'] . '».';
                    }
                    continue;
                }
                if ($field['type'] === 'list') {
                    $allowed = array_map('strval', array_column($field['values'], 'value'));
                    if (!in_array($value, $allowed, true)) {
                        $result['errors'][] = 'Выберите допустимое значение поля «' . $field['label'] . '».';
                        continue;
                    }
                }
                $lines[] = $field['label'] . ': ' . $value;
            }
        }
        if ($result['errors']) {
            return $result;
        }

        $mandatoryText = trim((string)($this->serviceRequirements['text'] ?? ''));
        if ($mandatoryText === '') {
            $result['errors'][] = 'Не настроен обязательный текст услуги. Обратитесь к администратору.';
            return $result;
        }

        $description = rtrim($description) . "\n\nСведения по заявке\n\n" . implode("\n\n", $lines);
        if (strpos($description, $mandatoryText) === false) {
            $description .= "\n\n" . $mandatoryText;
        }
        $result['description'] = $description;
        return $result;
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

        $results = \Kuratovru\Helpers\Helper::getDataFromIblock([
            'NAME' => 'ASC'
        ], [
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

        // Проверка до загрузки файлов и до new TaskServiceBuilder / build().
        $requirements = $this->prepareServiceRequirementDescription($service, $description, $request);
        if ($requirements['errors']) {
            return ['validationErrors' => $requirements['errors']];
                }
        $description = $requirements['description'];

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