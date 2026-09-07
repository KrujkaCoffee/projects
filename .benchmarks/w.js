{
    let responsibleSelects = [];
    let serviceBlock = null;
    let serviceDescriptionWrapper = null;
    let serviceDescription = null;

    let descriptionField = null;

    let marketingLogic = 0;

    let extraFieldsMap = [];

    let fieldsForConcatTitle = [];

    let createResponsibleBlock = (departments, depth) => {

        let select = document.createElement('select');
        select.dataset.depth = depth;
        select.classList.add('js-select');


        let option = document.createElement('option');
        option.value = '';
        option.innerText = 'Выберите';
        option.selected = true;
        option.disabled = true;
        select.insertAdjacentElement('beforeend', option);

        departments.forEach( department => {
            let option = document.createElement('option');
            option.value = department.value;
            option.innerText = department.label;
            select.insertAdjacentElement('beforeend', option);
        });

        responsibleSelects[responsibleSelects.length-1].insertAdjacentElement('afterend', select);

        responsibleSelects.push(select);
        selectAddHandler(select);
    };

    let deleteExcessResponsibleBlocks = depth => {
        let toRemove = [];
        responsibleSelects.forEach( (select, index) => {
            if ( select.dataset.depth >= depth ){
                toRemove.push(select);
                select.remove();
            }
        });

        toRemove.forEach(item => {
            responsibleSelects.splice(responsibleSelects.indexOf(item), 1);
        });
    };

    let deleteServiceBlock = () => {
        if (serviceBlock){
            serviceBlock.remove();
            serviceDescription.innerHTML = '';
            serviceDescriptionWrapper.style.height = 0;
        }

    };

    let getWordEnding = (number, declension) => {
        if (number % 100 >= 11 && number % 100 <= 19 || number % 10 == 0 || number % 10 >= 5 && number % 10 <= 9) {
            return declension[0];
        }
        if (number % 10 == 1) {
            return declension[1];
        }
        return declension[2];
    }

    let fullServiceDescription = (description, leadTime = '', timeAt = '', timeTo = '') => {

        let leadTimeFormatted;
        let schedule;

        if (leadTime) {
            leadTime = leadTime / 60;
            let mins = leadTime % 60,
                hours = (leadTime - mins) / 60;
            leadTimeFormatted = (hours ? hours + ' ' + getWordEnding(hours, ['часов', 'час', 'часа']) + ' ' : '') + (mins ? mins + ' ' + getWordEnding(mins, ['минут', 'минута', 'минуты']) : '');
        }

        if (timeAt && timeTo){
            schedule = `${timeAt} — ${timeTo}`;
        }

        serviceDescription.innerHTML = `${description} ${(leadTimeFormatted || schedule) && `<div class="service__description__properties" ${!description && `style="margin-top: 0;"`}>${leadTimeFormatted && `<div>Ожидаемое время решения проблемы</div><div>${leadTimeFormatted}</div>`}${schedule && `<div>Режим оказания услуги</div><div>${schedule}</div>`}</div>`}`;
        serviceDescriptionWrapper.style.height = serviceDescription.scrollHeight + 47 + 'px';
    }

    let createServiceBlock = (services, parentDepartment) => {

        let buildDiv = className => {
            let div = document.createElement('div');
            div.classList.add(className);
            return div;
        };

        let buildLabel = (text, id) => {
            let label = document.createElement('label');
            label.innerText = text;
            label.for = id;
            return label;
        };

        let buildSelect = (options, name, multiple = false) => {
            let select = document.createElement('select');
            select.name = name;
            select.id = name;
            select.multiple = multiple;
            if ( select.multiple === true ){
                select.classList.add('js-select-multiple');
            }
            select.classList.add('js-select');
            select.insertAdjacentElement('beforeend', buildOption('Выберите подходящее', '', 'selected', 'disabled'));
            options.forEach( option => {
                select.insertAdjacentElement('beforeend', buildOption(option.label, option.value));
            } );
            return select;
        };

        let buildOption = (label, value, selected = null, disabled = null) => {
            let option = document.createElement('option');
            option.innerText = label;
            option.value = value;
            if (selected){
                option.selected = true;
            }
            if (disabled){
                option.disabled = true;
            }
            return option;
        };

        let buildDeadlineInput = (deadline, timeAt, timeTo) => {
            let input = document.createElement('input');
            input.classList.add('input-deadline');
            input.type = 'text';
            input.name = 'input-deadline';
            input.id = 'input-deadline';
            let minDateTime = new Date((deadline * 1000));

            let getDate = dateTime => {
                return `${dateTime.getDate()}.${(dateTime.getMonth()+1)}.${dateTime.getFullYear()}`;
            };

            let getTime = dateTime => {
                return `${dateTime.getHours()}.${(dateTime.getMinutes())}`;
            }

            let flatpickrChange = (selectedDates, dateStr, instance) => {
                if ( (new Date(selectedDates).getDate()) === minDateTime.getDate() ){
                    instance.set('minTime', minTime);
                }else{
                    instance.set('minTime', timeAt);
                }
            }


            let minDate = getDate(minDateTime);
            let minTime = getTime(minDateTime);

            let options = {
                enableTime: true,
                dateFormat: "d.m.Y H:i",
                time_24hr: true,
                minDate: minDate,
                minTime: timeAt,
                maxTime: timeTo,
                onChange: flatpickrChange,
                disable: [
                    function(date) {
                        return (date.getDay() === 0 || date.getDay() === 6);
                    }
                ],
            }
            flatpickr(input, options);

            return input;
        };

        let buildInput = (name, id) => {
            let input = document.createElement('input');
            input.classList.add('input-deadline');
            input.type = 'text';
            input.name = name;
            input.id = id;
            return input;
        }

        let createField = (field) => {
            let input = null;

            switch (field.type){
                case 'text':
                    input = buildInput(field.name, field.name);
                    break;
                case 'list':
                    input = buildSelect(field.values, field.name);
                    break;
                case 'iblock_elements':
                    console.log(field);
                    input = buildSelect(field.values, field.name, field.multiple);
                    break;
                case 'projectpicker':
                    inputHidden = buildInput(field.name, field.name);
                    inputHidden.type = 'hidden';
                    const div = buildDiv('container-' + field.name);
                    div.classList.add('projectpicker-div');

                    const tagSelector = new BX.UI.EntitySelector.TagSelector({
                        multiple: false,
                        dialogOptions: {
                            context: 'services.main',
                            multiple: false,
                            tabs: [
                                {
                                    id: 'projectsCustom', title: 'Проекты', itemOrder: { title: 'asc' }
                                }
                            ],
                            items: field.values,
                            enableSearch: false,
                            dropdownMode: true,
                            compactView: false,

                        },

                        events: {
                            onTagAdd: (event) => {
                                inputHidden.value = event.getData().tag.id;
                            },
                            onTagRemove: (event) => {
                                inputHidden.value = 0;
                            },
                            onCreateButtonClick: (event) => {
                                BX.SidePanel.Instance.open("/company/personal/user/1/groups/create/?firstRow=project&refresh=N", {
                                    cacheable: false,
                                    allowChangeHistory: false,
                                    allowChangeTitle: false,
                                    width: 1200,
                                });

                            }
                        },
                        showCreateButton: true,
                    });



                    tagSelector.renderTo(div);

                    BX.addCustomEvent('SidePanel.Slider:onMessage', (event)=>{
                        const data = event.getData();

                        if ( data.projects ){
                            tagSelector.addTag({
                                id: data.projects[0].id,
                                title: data.projects[0].title,
                                entityId: 'project',
                            });
                        }
                    })



                    div.insertAdjacentElement('afterbegin', inputHidden);

                    hint = document.createElement('span');
                    hint.classList.add('projectpicker-hint');
                    hint.innerText = 'Задача будет создана в выбранном проекте';
                    div.insertAdjacentElement('beforeend', hint);

                    input = div;
                    break;
            }

            return input;
        }

        serviceBlock = buildDiv('container-grid');

        let deadlineDiv;

        let serviceDiv = buildDiv('container-grid-field');
        let serviceLabel = buildLabel('Тип услуги', 'select-service');
        let serviceSelect = buildSelect(services, 'select-service');
        serviceSelect.addEventListener('change', () => {
            let index = (serviceSelect.selectedIndex-1);
            fullServiceDescription(services[index].description, services[index].leadTime, services[index].timeAt, services[index].timeTo);

            //Внедряем дополнительные поля для элементов
            if ( extraFieldsConfig.elements.length ){
                extraFieldsConfig.elements.forEach( element => {

                    //Удаление всех доп. полей
                    element.fields.forEach(field => {
                        let existedField = document.querySelector('#' + field.name);
                        if ( existedField ){
                            existedField.closest('.container-grid-field').remove();
                        }
                    });

                    if ( element.values.some((elementId) => parseInt(elementId) === services[index].value ) ){
                        element.fields.forEach(field => {
                            let div = buildDiv('container-grid-field');
                            let label = buildLabel(field.label, field.name);

                            let input = createField(field);

                            div.insertAdjacentElement('afterbegin', input);
                            div.insertAdjacentElement('afterbegin', label);
                            serviceBlock.insertAdjacentElement('beforeend', div);

                        });
                    }
                });
            }

            if ( deadlineDiv ){
                deadlineDiv.remove();
            }

            deadlineDiv = buildDiv('container-grid-field');
            let deadlineLabel = buildLabel('Крайний срок', 'select-department');
            let deadlineInput = buildDeadlineInput(services[index].deadline, services[index].timeAt, services[index].timeTo);
            deadlineDiv.insertAdjacentElement('afterbegin', deadlineInput);
            deadlineDiv.insertAdjacentElement('afterbegin', deadlineLabel);

            serviceBlock.insertAdjacentElement('beforeend', deadlineDiv);


            if (serviceSelect.value == 240637){
                departmentDiv.hidden = true;
                priorityDiv.hidden = true;
                deadlineDiv.hidden = true;

                marketingLogic = 1;
            }else{
                departmentDiv.hidden = false;
                priorityDiv.hidden = false;
                deadlineDiv.hidden = false;

                marketingLogic = 0;
            }

            if (services[index].startText){
                descriptionField.value = services[index].startText;
            }


        });
        serviceDiv.insertAdjacentElement('afterbegin', serviceSelect);
        serviceDiv.insertAdjacentElement('afterbegin', serviceLabel);
        serviceBlock.insertAdjacentElement('beforeend', serviceDiv);

        let departmentDiv = buildDiv('container-grid-field');
        let departmentLabel = buildLabel('Ваше подразделение', 'select-department');
        let departmentSelect = buildSelect(departments, 'select-department');
        departmentDiv.insertAdjacentElement('afterbegin', departmentSelect);
        departmentDiv.insertAdjacentElement('afterbegin', departmentLabel);
        serviceBlock.insertAdjacentElement('beforeend', departmentDiv);

        let priorityDiv = buildDiv('container-grid-field');
        let priorityLabel = buildLabel('Приоритет', 'select-priority');
        let prioritySelect = buildSelect(priorities, 'select-priority');
        priorityDiv.insertAdjacentElement('afterbegin', prioritySelect);
        priorityDiv.insertAdjacentElement('afterbegin', priorityLabel);
        serviceBlock.insertAdjacentElement('beforeend', priorityDiv);

        //Внедряем дополнительные поля для разделов
        if ( extraFieldsConfig.sections.length ){
            extraFieldsConfig.sections.forEach( section => {
                if ( section.values.some((sectionId) => sectionId === parentDepartment ) ){

                    section.fields.forEach(field => {
                        let div = buildDiv('container-grid-field');
                        let label = buildLabel(field.label, field.name);

                        let input = createField(field);

                        div.insertAdjacentElement('afterbegin', input);
                        div.insertAdjacentElement('afterbegin', label);
                        serviceBlock.insertAdjacentElement('beforeend', div);

                    });
                }
            });
        }

        responsibleSelects[responsibleSelects.length-1].insertAdjacentElement('afterend', serviceBlock);
    };

    let selectAddHandler = ( select ) => {

        let prepareAjax = () => {
            isAjax = true;
            responsibleSelects.forEach(select => {
                select.disabled = true;
            });
        };

        let finishAjax = () => {
            isAjax = false;
            responsibleSelects.forEach(select => {
                select.disabled = false;
            });
        };

        let isAjax = false;
        select.addEventListener('change', async () => {
            if ( isAjax ) return false;
            prepareAjax();

            let data = new FormData();
            data.append('department', select.value);

            try {
                let response = await BX.ajax.runComponentAction(servicesComponentName, 'select', {
                    mode: 'class',
                    data: data,
                });


                if ( response.data.type === 'department' ){

                    deleteServiceBlock();
                    deleteExcessResponsibleBlocks(response.data.depth);
                    createResponsibleBlock(response.data.departments, response.data.depth);

                }else if (response.data.type === 'service'){

                    deleteServiceBlock();
                    deleteExcessResponsibleBlocks((select.dataset.depth+1));

                    if (response.data.services.length !== 0){
                        createServiceBlock(response.data.services, select.value);
                    }else{
                        alert('Данное подразделение не имеет активных услуг!');
                    }
                }
            } catch(err) {
                alert('Произошла неожиданная ошибка! Пожалуйста, попробуйте позже!');
            }

            finishAjax();
        });


    };

    let formHandler = () => {
        let form = document.querySelector('#service-form');
        let isAjax = false;
        if ( form ){
            form.addEventListener('submit', async e => {
                e.preventDefault();
                let department = form.querySelector('#select-department');
                let priority = form.querySelector('#select-priority');
                let service = form.querySelector('#select-service');
                let deadline = form.querySelector('#input-deadline');
                let description = form.querySelector('#description');

                if ( !marketingLogic ){
                    if ( !department || !priority || !service || !deadline ){
                        alert('Пожалуйста, выберите Отдел-испольнитель услуги!');
                        return false;
                    }


                    if ( !department.value ){
                        alert('Пожалуйста, выберите ваше подразделение!');
                        return false;
                    }

                    if ( !priority.value ){
                        alert('Пожалуйста, выберите приоритет вашей задачи!');
                        return false;
                    }

                    if ( !deadline.value ){
                        alert('Пожалуйста, установите крайний срок для задачи!');
                        return false;
                    }

                    //Валидация дополнительных полей
                    for ( let field of extraFieldsMap ){
                        let fieldForm = form.querySelector('#' + field.id);
                        if ( fieldForm && !fieldForm.value && field.required ){
                            alert('Пожалуйста, заполните поле "' + field.label + '"!');
                            return false;
                        }
                    }


                }

                if ( !service.value ){
                    alert('Пожалуйста, выберите тип услуги!');
                    return false;
                }



                if ( isAjax ) return;
                isAjax = true;

                //Загрузка дополнительных полей в описание
                description.value += "\n\n";
                extraFieldsMap.forEach(field => {
                    let fieldForm = form.querySelector('#' + field.id);
                    if ( fieldForm && !fieldsForConcatTitle.includes(field.id) ){
                        if ( fieldForm.tagName === 'SELECT' && fieldForm.multiple ){
                            description.value += field.label + ": " + Array.from(fieldForm.options).filter(o => o.selected).map(o => o.value).join('; ') + "\n\n";

                        }else{
                            description.value += field.label + ": " + fieldForm.value + "\n\n";
                        }
                    }
                });

                let data = new FormData(form);

                extraFieldsMap.forEach(field => {
                    let fieldForm = form.querySelector('#' + field.id);
                    if ( fieldForm ){
                        if ( field.type === 'projectpicker' ){
                            data.set('projectpickerField', field.id)
                        }
                    }
                });

                data.set('fields-for-concat-title', fieldsForConcatTitle)

                try {
                    let response = await BX.ajax.runComponentAction(servicesComponentName, 'send', {
                        mode: 'class',
                        data: data,
                    });

                    if ( response.data.userId && response.data.taskId ){
                        location.href = `/company/personal/user/${response.data.userId}/tasks/task/view/${response.data.taskId}/`;
                    }

                } catch(err) {
                    alert('Произошла неожиданная ошибка! Пожалуйста, попробуйте позже!');
                }


                isAjax = false;
            });

        }
    };

    let taskFilesCounter = () => {
        let taskFilesField = document.querySelector('#task-files');
        let taskFilesCounter = document.querySelector('#task-files-counter');

        if ( taskFilesField ){
            taskFilesField.addEventListener('change', () => {
                taskFilesCounter.innerText = "[" + taskFilesField.files.length + "]";
            })
        }

    }

    document.addEventListener('DOMContentLoaded', () => {

        flatpickr.localize(flatpickr.l10ns.ru);

        let mainSelect = document.querySelector('#select-responsible-department');

        descriptionField = document.querySelector('#description');

        if ( mainSelect ) {
            responsibleSelects.push(mainSelect);
            selectAddHandler(mainSelect);

            serviceDescriptionWrapper = document.querySelector('.service__description__wrapper');
            serviceDescription = document.querySelector('.service__description');

            formHandler();

            //Составить карту дополнительных полей
            extraFieldsConfig.sections.forEach( section => {
                section.fields.forEach(field => {
                    extraFieldsMap.push({
                        id: field.name,
                        required: field.required,
                        label: field.label,
                        type: field.type
                    });

                    if (field.type === "text" && field?.concat_title) {
                        fieldsForConcatTitle.push(field.name)
                    }
                })
            } );

            extraFieldsConfig.elements.forEach( section => {
                section.fields.forEach(field => {
                    extraFieldsMap.push({
                        id: field.name,
                        required: field.required,
                        label: field.label,
                        type: field.type
                    });

                    if (field.type === "text" && field?.concat_title) {
                        fieldsForConcatTitle.push(field.name)
                    }
                })
            } );

            //Счетчик для файлов
            taskFilesCounter();
        }

    });
}