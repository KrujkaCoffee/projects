<?php

namespace Kuratovru\Model\Service;

use Kuratovru\Util\Util;
use Bitrix\Iblock\Elements\ElementKelastServiceTable;
use Bitrix\Iblock\Model\Section;
use Bitrix\Main\Loader;

class Service{
    private static $iblockId = 44;

    private static $allFields = [
        'ID',
        'NAME',
        'ACTIVE',
        'EMPLOYEE',
        'AUDITORS',
        'ACCOMPLICES',
        'ALGORITHM',
        'PREVIEW_TEXT',
        'LEAD_TIME',
        'TIME_AT',
        'TIME_TO',
        'OLD_EMPLOYEE',
        'IBLOCK_SECTION_ID',
        'CHECKLISTS_TEXT',
        'CHECKLISTS_RESPONSIBLE',
        'START_TEXT'
    ];

    private static function includeModules(){
        Loader::includeModule('iblock');
    }

    private static function execute($filter){
        self::includeModules();
        $result = ElementKelastServiceTable::getList($filter);
        $objects = [];
        while ($row = $result->fetchObject()) {
            $objects[] = Util::objectToArray($row, $filter['select']);
        }
        return $objects;
    }

    private static function executeSections($filter){
        self::includeModules();

        $entity = Section::compileEntityByIblock(self::$iblockId);
        $sections = $entity::getList($filter);

        while ($section = $sections->fetch()):
            $results[] = $section;
        endwhile;

        return $results;
    }

    public static function getById($id){
        $filter = [
            'select' => self::$allFields,
            'filter' => ['ID' => $id],
        ];
        return self::execute($filter)[0];
    }

    public static function getBySectionId($id){
        $filter = [
            'select' => self::$allFields,
            'filter' => ['ACTIVE' => 'Y', 'IBLOCK_SECTION_ID' => $id],
            'cache' => [
                'ttl' => 36000,
                'cache_joins' => true,
            ]
        ];
        return self::execute($filter);
    }

    public static function getAll(){
        $filter = [
            'select' => ['NAME', 'IBLOCK_SECTION_ID', 'ID', 'PREVIEW_TEXT', 'LEAD_TIME', 'TIME_AT', 'TIME_TO'],
            'filter' => ['ACTIVE' => 'Y']
        ];
        return self::execute($filter);
    }

    public static function getChildSections( int $parentId = null ){
        $filter = [
            "select" => ['*'],
            "filter" => ["IBLOCK_ID" => self::$iblockId, "ACTIVE" => "Y", "GLOBAL_ACTIVE" => "Y", "IBLOCK_SECTION_ID" => $parentId]
        ];
        return self::executeSections($filter);
    }

    public static function updateEmployees($serviceId, $userId){
        $service = ElementKelastServiceTable::getList([
            'filter' => ['ID' => $serviceId],
            'limit' => 1,
            'cache' => ["ttl" => 3600],
        ])->fetchObject();
        $service->set('OLD_EMPLOYEE', $userId);
        $service->save();
    }

    public static function buildDeadline( int $serviceId ) : \DateTime {

        $fields = self::getById($serviceId);

        $timeAt = Util::getTimeArray($fields['TIME_AT']);
        $timeTo = Util::getTimeArray($fields['TIME_TO']);

        $minDate = new \DateTime('now');
        $dateStartWorking = (new \DateTime('now'))->setTime($timeAt['hours'], $timeAt['minutes']);
        $dateEndWorking = (new \DateTime('now'))->setTime($timeTo['hours'], $timeTo['minutes']);

        if ($dateStartWorking > $dateEndWorking)
            $dateEndWorking->modify('+1 day');

        $secondsForService = Util::getSecondFromServiceFormat($fields['LEAD_TIME']);

        while ( $secondsForService > 0 ):

            if (
                Util::isWeekend($minDate)
                ||
                !Util::isWorkTime($minDate, $dateStartWorking, $dateEndWorking)
            ):
                $dateStartWorking->modify('+1 day');
                $dateEndWorking->modify('+1 day');

                $minDate = clone $dateStartWorking;
            else:

                $currentWorkTime = $dateEndWorking->getTimestamp() - $minDate->getTimestamp();

                $diff = $secondsForService - $currentWorkTime;

                if ( $diff > 0 ):

                    $dateStartWorking->modify('+1 day');
                    $dateEndWorking->modify('+1 day');

                    $minDate = clone $dateStartWorking;

                    $secondsForService -= $currentWorkTime;
                else:
                    $minDate->setTimestamp( $minDate->getTimestamp() + $secondsForService );
                    break;
                endif;

            endif;

        endwhile;

        return $minDate;
    }

}