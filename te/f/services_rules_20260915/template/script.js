{
    let responsibleSelects = [];
    let serviceBlock = null;
    let serviceDescriptionWrapper = null;
    let serviceDescription = null;
    let serviceRulesBlock = null;
    let executorRulesBlock = null;
    let generalRulesNodes = [];

    let descriptionField = null;
    let descriptionHelp = null;
    let activeDescriptionKey = null;
    let activeDescriptionSchema = null;
    let unassignedDescription = '';
    const descriptionDrafts = new Map();

    let marketingLogic = 0;

    let extraFieldsMap = [];

    let fieldsForConcatTitle = [];

    // Текст правил выводится через textContent: разметка внутри текста не исполняется.
    const createRulesElement = (tag, className, text) => {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (text !== undefined) element.textContent = text;
        return element;
    };

    const appendRulesText = (container, text) => {
        let list = null;
        let lastItem = null;
        let nestedList = null;
        String(text || '').split(/\r?\n/).forEach(rawLine => {
            const line = rawLine.trim();
            if (!line) {
                list = null;
                lastItem = null;
                nestedList = null;
                return;
            }
            if (/^\*\s/.test(line)) {
                if (!list) {
                    list = createRulesElement('ul', 'service-rules__list');
                    container.appendChild(list);
                }
                lastItem = createRulesElement('li', '', line.replace(/^\*\s+/, ''));
                list.appendChild(lastItem);
                nestedList = null;
            } else if (/^-\s/.test(line) && lastItem) {
                if (!nestedList) {
                    nestedList = createRulesElement('ul', 'service-rules__sublist');
                    lastItem.appendChild(nestedList);
                }
                nestedList.appendChild(createRulesElement('li', '', line.replace(/^-\s+/, '')));
            } else {
                list = null;
                lastItem = null;
                nestedList = null;
                container.appendChild(createRulesElement('p', 'service-rules__paragraph', line));
            }
        });
    };

    const renderExecutorRules = sections => {
        if (!generalRulesNodes.length) return;
        if (!executorRulesBlock) {
            executorRulesBlock = createRulesElement('div', 'service-executor-rules');
            generalRulesNodes[0].insertAdjacentElement('beforebegin', executorRulesBlock);
        }
        executorRulesBlock.textContent = '';
        executorRulesBlock.hidden = !sections.length;
        // Исходные узлы остаются на странице: их текст, разметка и обработчики сохраняются.
        generalRulesNodes.forEach(node => node.classList.toggle('service-rules-original-hidden', !!sections.length));
        sections.forEach(section => {
            executorRulesBlock.appendChild(createRulesElement('div', 'column__title', section.title));
            const body = createRulesElement('div', 'service-rules service-rules--executor');
            // Первая строка полного текста уже показана в заголовке блока.
            const lines = String(section.text || '').split(/\r?\n/);
            if (lines[0].trim() === section.title) lines.shift();
            appendRulesText(body, lines.join('\n'));
            executorRulesBlock.appendChild(body);
        });
    };

    const appendRequirementsTable = (body, fields) => {
        body.appendChild(createRulesElement('p', 'service-rules__paragraph',
            'Заполните строки в описании проблемы. Сохраните заголовки и двоеточия.'));
        const table = createRulesElement('table', 'service-rules__table');
        const thead = document.createElement('thead');
        const heading = document.createElement('tr');
        ['Что указать', 'Требование'].forEach(text => {
            const th = createRulesElement('th', '', text);
            th.scope = 'col';
            heading.appendChild(th);
        });
        thead.appendChild(heading);
        table.appendChild(thead);
        const tbody = document.createElement('tbody');
        fields.filter(field => field.required || field.required_if).forEach(field => {
            const row = document.createElement('tr');
            const label = createRulesElement('th', '', field.label);
            label.scope = 'row';
            row.appendChild(label);
            const cell = document.createElement('td');
            cell.appendChild(createRulesElement('strong', 'service-rules__requirement',
                field.required_if ? 'Для новой продукции' : 'Обязательно'));
            cell.appendChild(createRulesElement('span', '', field.hint));
            row.appendChild(cell);
            tbody.appendChild(row);
        });
        table.appendChild(tbody);
        body.appendChild(table);
    };

    const renderServiceRules = (sections, schema = null) => {
        sections = Array.isArray(sections) ? sections : [];
        renderExecutorRules(sections.filter(section => section.placement === 'general'));
        if (!serviceDescriptionWrapper) return;
        if (!serviceRulesBlock) {
            serviceRulesBlock = createRulesElement('div', 'service-rules');
            serviceRulesBlock.setAttribute('aria-label', 'Правила выбранной услуги');
            // Требования находятся вне обёртки описания с фиксированной высотой.
            serviceDescriptionWrapper.insertAdjacentElement('afterend', serviceRulesBlock);
        }
        serviceRulesBlock.textContent = '';
        serviceRulesBlock.hidden = true;
        sections = sections.filter(section => section.placement !== 'general');
        if (!sections.length) return;

        sections.forEach((section, index) => {
            const kind = ['primary', 'standard', 'notice', 'details'].includes(section.kind)
                ? section.kind : 'standard';
            const isDetails = kind === 'details';
            const panel = createRulesElement(isDetails ? 'details' : 'section',
                'service-rules__section service-rules__section--' + kind);
            const title = createRulesElement(isDetails ? 'summary' : 'h3',
                'service-rules__title', section.title);
            title.id = 'service-rules-title-' + index;
            if (!isDetails) panel.setAttribute('aria-labelledby', title.id);
            panel.appendChild(title);
            const body = createRulesElement('div', 'service-rules__body');
            if (kind === 'primary' && schema && schema.fields) {
                appendRequirementsTable(body, schema.fields);
            } else {
                appendRulesText(body, section.text);
            }
            panel.appendChild(body);
            serviceRulesBlock.appendChild(panel);
        });
        serviceRulesBlock.hidden = false;
    };

    const saveDescriptionDraft = () => {
        if (!descriptionField) return;
        if (activeDescriptionKey !== null) {
            descriptionDrafts.set(activeDescriptionKey, descriptionField.value);
        } else {
            unassignedDescription = descriptionField.value;
        }
    };

    const updateDescriptionHelp = () => {
        const hasTemplate = !!activeDescriptionSchema;
        descriptionField.classList.toggle('service-description--template', hasTemplate);
        if (descriptionHelp) descriptionHelp.hidden = !hasTemplate;
    };

    const selectServiceDescription = service => {
        saveDescriptionDraft();
        activeDescriptionKey = String(service.value);
        activeDescriptionSchema = service.hasServiceRules && service.descriptionSchema
            && Array.isArray(service.descriptionSchema.fields) ? service.descriptionSchema : null;
        if (descriptionDrafts.has(activeDescriptionKey)) {
            // В том числе восстанавливаем намеренно очищенный текст.
            descriptionField.value = descriptionDrafts.get(activeDescriptionKey);
        } else {
            const parts = [];
            if (service.startText) parts.push(String(service.startText).trim());
            if (unassignedDescription.trim()) parts.push(unassignedDescription);
            if (activeDescriptionSchema) {
                const seedLines = parts.join('\n\n').split(/\r?\n/);
                const missingFields = activeDescriptionSchema.fields.filter(field =>
                    !seedLines.some(line => descriptionLinePattern(field).test(line)));
                if (missingFields.length) parts.push(missingFields.map(field => field.label + ': ').join('\n\n'));
            }
            descriptionField.value = parts.join('\n\n');
        }
        updateDescriptionHelp();
    };

    const resetServiceDescription = () => {
        saveDescriptionDraft();
        activeDescriptionKey = null;
        activeDescriptionSchema = null;
        if (descriptionField) {
            descriptionField.value = unassignedDescription;
            updateDescriptionHelp();
        }
    };

    const descriptionLinePattern = field => new RegExp(
        '^\\s*' + field.label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\s*:[\\t ]*(.*)$', 'iu');

    const validateServiceDescription = (description, schema) => {
        if (!schema || !Array.isArray(schema.fields)) return [];
        const values = {};
        const seen = new Set();
        const errors = [];
        let current = null;
        const patterns = schema.fields.map(field => ({field, pattern: descriptionLinePattern(field)}));
        description.split(/\r\n|[\n\r\v\f\u0085\u2028\u2029]/).forEach(line => {
            let matched = false;
            for (const {field, pattern} of patterns) {
                const match = line.match(pattern);
                if (!match) continue;
                current = field.key;
                if (seen.has(current)) errors.push('Строка «' + field.label + '» повторяется. Объедините сведения в одном блоке.');
                seen.add(current);
                values[current] = match[1];
                matched = true;
                break;
            }
            if (!matched && current !== null) values[current] += '\n' + line;
        });
        Object.keys(values).forEach(key => {
            values[key] = values[key].replace(/[\s\p{Z}\u200B\uFEFF]+/gu, ' ').trim();
        });
        schema.fields.forEach(field => {
            if (field.choices && values[field.key] !== undefined) {
                const choice = field.choices.find(item => item.toLowerCase() === values[field.key].toLowerCase());
                if (choice) values[field.key] = choice;
            }
        });
        schema.fields.forEach(field => {
            const required = field.required_if
                ? (values[field.required_if.key] || '') === field.required_if.equals : !!field.required;
            const value = values[field.key] || '';
            const empty = !value || /^[\p{P}\p{S}\s]+$/u.test(value) || /^\[?заполните\]?$/iu.test(value);
            if (required && empty) {
                errors.push('Заполните строку «' + field.label + '» в описании проблемы (сохраните заголовок и двоеточие).');
            } else if (value && field.choices && !field.choices.includes(value)) {
                errors.push('В строке «' + field.label + '» укажите ' + field.choices.join(' или ') + '.');
            }
        });
        return [...new Set(errors)];
    };

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
        renderServiceRules([]);
        resetServiceDescription();
        marketingLogic = 0;
        if (serviceBlock){
            serviceBlock.remove();
            serviceBlock = null;
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

    let createServiceBlock = (services, parentDepartment, serviceRules = []) => {

        let buildDiv = className => {
            let div = document.createElement('div');
            div.classList.add(className);
            return div;
        };

        let buildLabel = (text, id) => {
            let label = document.createElement('label');
            label.innerText = text;
            label.htmlFor = id;
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
                    const inputHidden = buildInput(field.name, field.name);
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

                    const hint = document.createElement('span');
                    hint.classList.add('projectpicker-hint');
                    hint.innerText = 'Задача будет создана в выбранном проекте';
                    div.insertAdjacentElement('beforeend', hint);

                    input = div;
                    break;
            }

            if (input) input.setAttribute('aria-required', field.required ? 'true' : 'false');
            return input;
        }

        serviceBlock = buildDiv('container-grid');

        let deadlineDiv;

        let serviceDiv = buildDiv('container-grid-field');
        let serviceLabel = buildLabel('Тип услуги', 'select-service');
        let serviceSelect = buildSelect(services, 'select-service');
        serviceSelect.addEventListener('change', () => {
            let index = (serviceSelect.selectedIndex-1);
            if (!services[index]) {
                renderServiceRules([]);
                resetServiceDescription();
                return;
            }
            fullServiceDescription(services[index].description, services[index].leadTime, services[index].timeAt, services[index].timeTo);
            selectServiceDescription(services[index]);
            renderServiceRules(services[index].hasServiceRules ? serviceRules : [], activeDescriptionSchema);

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

                    if ( element.values.some((elementId) => String(elementId) === String(services[index].value) ) ){
                        element.fields.forEach(field => {
                            let div = buildDiv('container-grid-field');
                            let label = buildLabel(field.label + (field.required ? ' *' : ''), field.name);

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
                if ( section.values.some((sectionId) => String(sectionId) === String(parentDepartment) ) ){

                    section.fields.forEach(field => {
                        let div = buildDiv('container-grid-field');
                        let label = buildLabel(field.label + (field.required ? ' *' : ''), field.name);

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
            // Сразу возвращаем общие правила, не дожидаясь ответа сервера.
            deleteServiceBlock();

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
                    deleteExcessResponsibleBlocks(Number(select.dataset.depth) + 1);

                    if (response.data.services.length !== 0){
                        createServiceBlock(response.data.services, select.value, response.data.serviceRules || []);
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
                        if ( fieldForm && field.required && (!fieldForm.value.trim()
                            || (field.type === 'projectpicker' && fieldForm.value === '0')) ){
                            alert('Пожалуйста, заполните поле "' + field.label + '"!');
                            return false;
                        }
                    }


                }

                if ( !service || !service.value ){
                    alert('Пожалуйста, выберите тип услуги!');
                    return false;
                }



                const descriptionErrors = validateServiceDescription(description.value, activeDescriptionSchema);
                if (descriptionErrors.length) {
                    alert(descriptionErrors.join('\n'));
                    description.focus();
                    return false;
                }

                if ( isAjax ) return;
                isAjax = true;

                // Не меняем textarea: повторная попытка отправки не дублирует допполя.
                let extraDescription = '';
                extraFieldsMap.forEach(field => {
                    let fieldForm = form.querySelector('#' + field.id);
                    if ( fieldForm && !fieldsForConcatTitle.includes(field.id) ){
                        if ( fieldForm.tagName === 'SELECT' && fieldForm.multiple ){
                            extraDescription += field.label + ": " + Array.from(fieldForm.options).filter(o => o.selected).map(o => o.value).join('; ') + "\n\n";

                        }else{
                            extraDescription += field.label + ": " + fieldForm.value + "\n\n";
                        }
                    }
                });

                let data = new FormData(form);
                // Для целевых услуг сервер сначала проверит сам шаблон, затем добавит допполя.
                data.set('description', activeDescriptionSchema ? description.value
                    : description.value + (extraDescription ? '\n\n' + extraDescription : ''));
                data.set('extra_fields_description', extraDescription);

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

                    if (Array.isArray(response.data.validationErrors) && response.data.validationErrors.length) {
                        alert(response.data.validationErrors.join('\n'));
                        description.focus();
                    }

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
        if (descriptionField) {
            unassignedDescription = descriptionField.value;
            descriptionHelp = createRulesElement('p', 'service-description-help',
                'Заполните строки после двоеточий. Если особых условий нет, укажите «Нет». Направление деятельности нужно только для абсолютно новой продукции.');
            descriptionHelp.hidden = true;
            descriptionField.insertAdjacentElement('beforebegin', descriptionHelp);
        }

        if ( mainSelect ) {
            responsibleSelects.push(mainSelect);
            selectAddHandler(mainSelect);

            serviceDescriptionWrapper = document.querySelector('.service__description__wrapper');
            serviceDescription = document.querySelector('.service__description');
            // При сужении колонки текст переносится: обновляем высоту, чтобы правила его не перекрывали.
            if (serviceDescription && serviceDescriptionWrapper && typeof ResizeObserver !== 'undefined') {
                new ResizeObserver(() => {
                    if (serviceBlock && serviceDescription.innerHTML) {
                        serviceDescriptionWrapper.style.height = serviceDescription.scrollHeight + 47 + 'px';
                    }
                }).observe(serviceDescription);
            }
            const generalBody = document.querySelector('.page__description__wrapper > .page__description');
            const generalTitle = generalBody && generalBody.previousElementSibling;
            if (generalTitle && generalTitle.classList.contains('column__title')) {
                generalRulesNodes = [generalTitle, generalBody];
            }

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
