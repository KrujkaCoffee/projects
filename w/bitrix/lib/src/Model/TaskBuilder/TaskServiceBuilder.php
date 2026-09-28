<?php

namespace Kuratovru\Model\TaskBuilder;

use Kuratovru\Model\Service\Service;
use Kuratovru\Model\Task\Task;
use Kuratovru\Util\Util;
use Kuratovru\AlgorithmEmployee\AlgorithmFactory;

/**
 * Class TaskServiceBuilder
 * @package FL\TaskBuilder
 */
class TaskServiceBuilder implements TaskBuilderInterface
{
    protected $serviceId;
    protected $title = '';
    protected $timeFrom;
    protected $timeTo;
    protected $tags;
    protected $description;
    protected $leadTime;
    protected $createdBy;
    protected $employees;
    protected $auditors;
    protected $accomplices;
    protected $algorithm;
    protected $responsible;
    protected $prevEmployee;
    protected $taskControl = true;
    protected $deadLine;
    protected $taskId;
    protected $startDate;
    protected $workGroup;
    protected $files = [];
    protected $department;
    protected $priority;

    protected $checklists = [];
    protected $departmentService;

    /**
     * TaskServiceBuilder constructor.
     * @param integer $serviceId
     */
    public function __construct($serviceId)
    {
        $this->serviceId = $serviceId;
        $this->createdBy = Task::getDefaultUser();
        $this->workGroup = 20;
        $this->init();
    }

    protected function init()
    {
        $service = Service::getById($this->serviceId);

        $this->title = 'Услуга: ' . $service['NAME'];
        $this->tags = ['Услуга ' . $this->serviceId, 'Услуга', $service['NAME']];

        $this->timeFrom = Util::getSecondFromServiceFormat($service['TIME_AT']);
        $this->timeTo = Util::getSecondFromServiceFormat($service['TIME_TO']);
        $this->leadTime = Util::getSecondFromServiceFormat($service['LEAD_TIME']);
        $this->employees = $service['EMPLOYEE'];
        $this->accomplices = $service['ACCOMPLICES'];
        $this->auditors = $service['AUDITORS'];
        $this->prevEmployee = $service['OLD_EMPLOYEE'];
        $this->algorithm = $service['ALGORITHM'];
        $this->deadLine = Service::buildDeadline($this->serviceId);

        if ( !empty($service['CHECKLISTS_TEXT']) ):
            $parentKey = uniqid();
            $this->checklists[$parentKey] = [
                'NODE_ID' => $parentKey,
                'PARENT_NODE_ID' => 0,
                'COPIED_ID' => 'undefined',
                'TITLE' => 'Чек-лист 1',
                'SORT_INDEX' => 0,
                'IS_COMPLETE' => false,
                'IS_IMPORTANT' => false,
            ];

            for ( $i = 0; $i < count( $service['CHECKLISTS_TEXT'] ); $i++ ):
                if ( isset($service['CHECKLISTS_RESPONSIBLE'][$i]) ):

                    $userId = $service['CHECKLISTS_RESPONSIBLE'][$i] == 1 ? \Bitrix\Main\Engine\CurrentUser::get()->getId() : $service['CHECKLISTS_RESPONSIBLE'][$i];

                    $user = \Bitrix\Main\UserTable::getById($userId)->fetch();
                    $title = $service['CHECKLISTS_TEXT'][$i]. ' ' . $user['NAME'] . ' ' . $user['LAST_NAME'];
                    $members = [
                        $userId  => [
                            'TYPE' => 'accomplice',
                            'NAME' => $user['NAME'] . ' ' . $user['LAST_NAME']
                        ]
                    ];
                else:
                    $user = null;
                    $title = $service['CHECKLISTS_TEXT'][$i];
                    $members = [];
                endif;

                $currentKey = uniqid();
                $this->checklists[$currentKey] = [
                    'NODE_ID' => $currentKey,
                    'PARENT_NODE_ID' => $parentKey,
                    'COPIED_ID' => 'undefined',
                    'TITLE' => $title,
                    'SORT_INDEX' => $i,
                    'IS_COMPLETE' => false,
                    'IS_IMPORTANT' => false,
                    'MEMBERS' => $members,
                ];
            endfor;
        endif;



        $this->executeAlgorithm();
    }

    protected function executeAlgorithm()
    {
        $algorithm = AlgorithmFactory::getAlgorithm($this->algorithm);
        $this->responsible = $algorithm->getNewEmployee($this->employees, $this->prevEmployee);
    }

    /**
     * Создает задачу.
     */
    public function build()
    {
        $taskFields = [];
        $taskFields['TITLE'] = $this->title;
        $taskFields['DESCRIPTION'] = $this->description;
        $taskFields['TAGS'] = $this->tags;
        $taskFields['TASK_CONTROL'] = $this->taskControl;
        $taskFields['ALLOW_TIME_TRACKING'] = 'N';
        $taskFields['DEADLINE'] = $this->deadLine->format('d.m.Y H:i:s');
        $taskFields['RESPONSIBLE_ID'] = $this->responsible;
        $taskFields['CREATED_BY'] = $this->createdBy;
        $taskFields['GROUP_ID'] = $this->workGroup;
        $taskFields['AUDITORS'] = $this->auditors;
        $taskFields['ACCOMPLICES'] = $this->accomplices;

        $taskFields['UF_TASK_WEBDAV_FILES'] = $this->files;
        $taskFields['UF_TASK_PRIOPRITY'] = $this->priority;
        $taskFields['UF_TASK_DEPARTMENT'] = $this->department;
        $taskFields['UF_TASK_SERVICE'] = $this->serviceId;
        $taskFields['UF_TASK_SERVICE_DEPARTMENT'] = $this->departmentService;

        $taskId = Task::create($taskFields);
        $this->taskId = $taskId;
        Service::updateEmployees($this->getService(), $this->getResponsible());

        if ( !empty($this->checklists) ):
            \Bitrix\Tasks\CheckList\Task\TaskCheckListFacade::merge($taskId, 1, $this->checklists);
        endif;

        return $this;
    }

    /**
     * @return int
     */
    public function getService(){
        return $this->serviceId;
    }

    /**
     * @param integer $id
     * @return $this
     */
    public function setService($id)
    {
        $this->serviceId = $id;
        $this->init();
        return $this;
    }

    public function getWorkGroup(){
        return $this->workGroup;
    }

    /**
     * @param integer $id
     * @return $this
     */
    public function setWorkGroup($id)
    {
        $this->workGroup = $id;
        return $this;
    }

    /**
     * @param integer $id ID алгоритма в базе данных
     * @return $this
     */
    public function setAlgorithm($id)
    {
        $this->algorithm = $id;
        $this->executeAlgorithm();
        return $this;
    }

    /**
     * @return string
     */
    public function getTitle()
    {
        return $this->title;
    }

    /**
     * @param string $title
     * @return $this
     */
    public function setTitle($title)
    {
        $this->title = $title;
        return $this;
    }

    /**
     * @return array
     */
    public function getTags()
    {
        return $this->tags;
    }

    /**
     * @param string $tag
     * @return $this
     */
    public function addTag($tag)
    {
        $this->tags[] = $tag;
        return $this;
    }

    /**
     * @param array $tags
     * @return $this
     */
    public function setTags($tags)
    {
        $this->tags = $tags;
        return $this;
    }

    /**
     * @param string $description
     * @return $this
     */
    public function setDescription($description)
    {
        $this->description = $description;
        return $this;
    }

    public function getDescription()
    {
        return $this->description;
    }

    /**
     * @param integer $id ID ответсветнного
     * @return $this
     */
    public function setResponsible($id)
    {
        $this->responsible = $id;
        return $this;
    }

    /**
     * @return integer
     */
    public function getResponsible()
    {
        return $this->responsible;
    }

    /**
     * @param integer $id ID создателя задачи
     * @return $this
     */
    public function setCreatedBy($id)
    {
        $this->createdBy = $id;
        return $this;
    }

    /**
     * @return integer
     */
    public function getCreatedBy()
    {
        return $this->createdBy;
    }

    /**
     * @param boolean $flag
     * @return $this
     */
    public function setTaskControl($flag)
    {
        $this->taskControl = $flag;
        return $this;
    }

    /**
     * @return boolean
     */
    public function getTaskControl()
    {
        return $this->taskControl;
    }

    /**
     * @return integer
     */
    public function getTaskId()
    {
        return $this->taskId;
    }

    /**
     * @return \DateTime
     */
    public function getStartDate()
    {
        return $this->startDate;
    }

    /**
     * @return \DateTime
     */
    public function getDeadLine()
    {
        return $this->deadLine;
    }

    public function setDeadLine( \DateTime $deadLine ){
        $this->deadLine = $deadLine;
        return $this;
    }
    /**
     * @param integer $fileId
     * @return $this
     */
    public function addFile($fileId){
        $this->files[] = 'n'.$fileId;
        return $this;
    }

    /**
     * @return mixed
     */
    public function getDepartment(){
        return $this->department;
    }

    /**
     * @param mixed $department
     */
    public function setDepartment($department){
        $this->department = $department;
        return $this;
    }

    /**
     * @return mixed
     */
    public function getPriority(){
        return $this->priority;
    }

    /**
     * @param mixed $priority
     */
    public function setPriority($priority){
        $this->priority = $priority;
        return $this;
    }

    /**
     * @return mixed
     */
    public function getDepartmentService(){
        return $this->departmentService;
    }

    /**
     * @param mixed $departmentService
     */
    public function setDepartmentService($departmentService){
        $this->departmentService = $departmentService;
        return $this;
    }

}