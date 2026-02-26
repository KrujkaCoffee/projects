OUTPUT_PARAMS = {
    'edinica_rashoda_imya'
    : {'view': True, 'header': 'Единица расхода имя', 'dimension': '', 'comment': 'Промежуточные расчеты',
       'group_name': 'Промежуточные расчеты',
       'formula': {'expr': '=IF(E10="т/ч","Расход среды G, т/ч",IF(E10="кг/с","Расход среды G, кг/с"))', 'cell': 'O5'},
       'accuracy': 4},
    'molyarnaya_massa_sredy_kg_mol'
    : {'view': True, 'header': 'Молярная масса среды, кг/моль', 'dimension': 'кг/моль', 'comment': '',
       'group_name': 'Промежуточные расчеты',
       'formula': {'expr': '=8.314459/O29', 'cell': 'O6'}, 'accuracy': 4},
    'plotnost_sredy_kg_m3'
    : {'view': True, 'header': 'Плотность среды, кг/м3', 'dimension': 'кг/м3', 'comment': '',
       'group_name': 'Промежуточные расчеты',
       'formula': {'expr': '=O26*O6/(8.314459*O135)*1000000', 'cell': 'O7'}, 'accuracy': 4},
    'skorost_para_iz_truby_m_s'
    : {'view': True, 'header': 'Скорость пара из трубы, м/с', 'dimension': 'м/с', 'comment': '',
       'group_name': 'Промежуточные расчеты',
       'formula': {'expr': '=O24/(O7*(PI()*E36^2/4))', 'cell': 'O8'}, 'accuracy': 4},
    'v_skorost_mezhdu_plastinami_m_s'
    : {'view': True, 'header': 'v - скорость между пластинами, м/с', 'dimension': 'м/с', 'comment': '',
       'group_name': 'Промежуточные расчеты',
       'formula': {'expr': '=(O24*O29*O135)/((((O24^2*O29*O135*E62*E29)/(2*O140*O141^0.5)^2)+O152^2)^0.5*O140)',
                   'cell': 'O10'}, 'accuracy': 4},
    'plotnost_rho_po_rashodu_i_geometrii'
    : {'view': True, 'header': 'ρ', 'dimension': 'кг/м³', 'comment': 'plotnost_rho_po_rashodu_i_geometrii',
       'formula': {'expr': '=(((O24^2*O29*O135*E62*E29)/(2*O140*O141^0,5)^2)+E63^2)^0,5/(O29*O135)', 'cell': 'O11'},
       'accuracy': 4, 'group_name': 'Промежуточные расчеты'},
    'plotnost_rho_po_idealnomu_gazu'
    : {'view': True, 'header': 'ρ', 'dimension': '', 'comment': 'ф. (5.177)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=O266/(O254*O256)', 'cell': 'O270'}, 'accuracy': 4},
    'epsilon_1'
    : {'view': True, 'header': 'ε (1)', 'dimension': '', 'comment': '', 'group_name': 'Промежуточные расчеты',
       'formula': {'expr': '=(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1))', 'cell': 'O12'}, 'accuracy': 4},
    'k'
    : {'view': True, 'header': 'K ', 'dimension': '', 'comment': '', 'group_name': 'Промежуточные расчеты',
       'formula': {'expr': '=($O$31+1)/(2*$O$31)*(O24*O28)/O12', 'cell': 'O13'}, 'accuracy': 4},
    'y_1'
    : {'view': True, 'header': 'y (1)', 'dimension': '', 'comment': '', 'group_name': 'Промежуточные расчеты',
       'formula': {'expr': '=((($O$31+1)/2)^(1/($O$31-1)))/(1-($O$31-1)/($O$31+1))', 'cell': 'O14'}, 'accuracy': 4},
    'y'
    : {'view': True, 'header': 'y', 'dimension': '', 'comment': '', 'group_name': 'Промежуточные расчеты',
       'formula': {'expr': '=O13/(O92*O174)', 'cell': 'O15'}, 'accuracy': 4},
    'λ'
    : {'view': True, 'header': 'λ', 'dimension': '', 'comment': '', 'group_name': 'Промежуточные расчеты',
       'formula': {'expr': '=(-1+(1+4*(($O$31-1)/($O$31+1))*O12^2*O15^2)^0.5)/(2*(($O$31-1)/($O$31+1))*O12*O15)',
                   'cell': 'O16'}, 'accuracy': 4},

    'udelnyj_obem_m3_kg_out2'
    : {'view': True, 'header': 'Удельный объем, м3/кг', 'dimension': 'м3/кг',
       'comment': 'Удельный объем при заданной температуре и атмосферном давлении', 'accuracy': 3,
       'group_name': 'Отдельное окно расчета'},
    'massovyj_rashod_kg_s_out2'
    : {'view': True, 'header': 'Массовый расход, кг/с', 'dimension': 'кг/с', 'comment': '', 'accuracy': 3,
       'group_name': 'Отдельное окно расчета'},
    'diametr_shg_m_out2'
    : {'view': True, 'header': 'Диаметр ШГ, м', 'dimension': 'м', 'comment': '', 'accuracy': 3,
       'group_name': 'Отдельное окно расчета'},

    'ploschad_vyhoda_shg_m2'
    : {'view': True, 'header': 'Площадь выхода ШГ, м2', 'dimension': 'м2', 'comment': 'Отдельное окно расчета',
       'group_name': 'Отдельное окно расчета',
       'formula': {'expr': '=PI()*E59^2/4', 'cell': 'O18'}, 'accuracy': 4},
    'skorost_na_vyhode_shg_m_s'
    : {'view': True, 'header': 'Скорость на выходе ШГ, м/с', 'dimension': 'м/с', 'comment': '',
       'group_name': 'Отдельное окно расчета',
       'formula': {'expr': '=E58*E57/O18', 'cell': 'O19'}, 'accuracy': 4},
    'r_reaktivnye_sily_n'
    : {'view': True, 'header': 'R, реактивные силы, Н', 'dimension': '', 'comment': '',
       'group_name': 'Отдельное окно расчета',
       'formula': {'expr': '=O19^2*O18/E57', 'cell': 'O20'}, 'accuracy': 4},
    'sreda_2'
    : {'view': True, 'header': 'Среда', 'dimension': '', 'comment': 'Дроссельный блок',
       'group_name': 'Дроссельный блок',
       'formula': {'expr': '=E9', 'cell': 'O23'}, 'accuracy': 4},
    'rashod_sredy_g_kg_s'
    : {'view': True, 'header': 'Расход среды g, кг/с', 'dimension': 'кг/с', 'comment': '',
       'group_name': 'Дроссельный блок',
       'formula': {'expr': '=IF(E10="кг/с",E11,IF(E10="т/ч",ROUNDUP(E11*1000/3600,2)))', 'cell': 'O24'}, 'accuracy': 4},
    'temperatura_sredy_s_2'
    : {'view': True, 'header': 'Температура среды, с', 'dimension': 'с', 'comment': '',
       'group_name': 'Дроссельный блок',
       'formula': {'expr': '=E12', 'cell': 'O25'}, 'accuracy': 4},
    'davlenie_na_vhode_v_shg_pi_abs_mpa'
    : {'view': True, 'header': 'Давление на входе в шг pi (абс), мпа', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Дроссельный блок',
       'formula': {'expr': '=E13', 'cell': 'O26'}, 'accuracy': 4},
    'davlenie_na_vyhode_iz_shg_pe_mpa'
    : {'view': True, 'header': 'Давление на выходе из шг pe, мпа', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Дроссельный блок',
       'formula': {'expr': '=O153*10^-6', 'cell': 'O27'}, 'accuracy': 4},
    'kriticheskaya_skorost_skr_m_s'
    : {'view': True, 'header': 'Критическая скорость скр, м/с', 'dimension': 'м/с', 'comment': '',
       'group_name': 'Дроссельный блок',
       'formula': {'expr': '=(2*O29*(E12+273)*($O$31/($O$31+1)))^0.5', 'cell': 'O28'}, 'accuracy': 4},
    'gazovaya_postoyannaya_m2_s2_k'
    : {'view': True, 'header': 'Газовая постоянная , м2/с2*к', 'dimension': '', 'comment': '',
       'group_name': 'Дроссельный блок',
       'formula': {
           'expr': '=IF(E9="Пар","461,5",IF(E9="Природный газ","508",IF(E9="Воздух","287",IF(E9="Углекислый газ (СО2)","188,9",IF(E9="Азот (N2)","296,8",IF(E9="Кислород (O2)","259,7",IF(E9="Аргон (Ar)",208)))))))',
           'cell': 'O29'}, 'accuracy': 4},
    'znachenie_p_drosselnogo_bloka'
    : {'view': True, 'header': 'Значение п дроссельного блока', 'dimension': '', 'comment': '',
       'group_name': 'Дроссельный блок',
       'formula': {'expr': '=E13/O27', 'cell': 'O30'}, 'accuracy': 4},
    'koeffcient_adiabaty'
    : {'view': True, 'header': 'Коэффциент адиабаты', 'dimension': '', 'comment': '', 'group_name': 'Дроссельный блок',
       'formula': {
           'expr': '=IF(E9="Пар","1,3",IF(E9="Природный газ","1,4",IF(E9="Воздух","1,4",IF(E9="Углекислый газ (СО2)","1,3",IF(E9="Азот (N2)","1,4",IF(E9="Кислород (O2)","1,4",IF(E9="Аргон (Ar)",1.67)))))))',
           'cell': 'O31'}, 'accuracy': 4},
    'kolichestvo_stupenej_drosselirovaniya_j'
    : {'view': True, 'header': 'Количество ступеней дросселирования j', 'dimension': 'шт',
       'comment': 'Параметры дроссельного блока',
       'group_name': 'Параметры дроссельного блока',
       'formula': {'expr': '=E17', 'cell': 'O34'}, 'accuracy': 4},
    'maksimalnoe_kolichestvo_otverstij_kmah_v_drosselnoj_reshetke_sht'
    : {'view': True, 'header': 'Максимальное количество отверстий кмах в дроссельной решетке, шт', 'dimension': 'шт',
       'comment': '',
       'group_name': 'Параметры дроссельного блока',
       'formula': {'expr': '=E18', 'cell': 'O35'}, 'accuracy': 4},
    'gradient_skorosti_w'
    : {'view': True, 'header': 'Градиент скорости w', 'dimension': 'м/с',
       'comment': 'Показатель градиента скорости w задается и должен быть строго больше 1 и меньше максимального значения wmax\n\nНаименьшее значение w соответствует чрезмерному вкладу последних ступеней в суммарный шум, а наибольшие - ведут к неограниченному росту габаритов ШГ',
       'group_name': 'Параметры дроссельного блока',
       'formula': {'expr': '=IF($E$17=1,E19,ROUND(O40-0.01,2))', 'cell': 'O38'}, 'accuracy': 4},
    'maksimalnyj_gradient_skorosti_wmax'
    : {'view': True, 'header': 'Максимальный градиент скорости wmax', 'dimension': 'м/с', 'comment': '',
       'group_name': 'Параметры дроссельного блока',
       'formula': {'expr': '=IF(E17=1,"",O30^(2/(O34*(O34-1))))', 'cell': 'O39'}, 'accuracy': 4},
    'rekomenduemoe_nachalnoe_znachenie_w'
    : {'view': True, 'header': 'Рекомендуемое начальное значение w', 'dimension': '', 'comment': '',
       'group_name': 'Параметры дроссельного блока',
       'formula': {'expr': '=IF(E17=1,"",O39^0.875)', 'cell': 'O40'}, 'accuracy': 4},
    'otnositelnyj_perepad_davleniya_na_poslednej_reshetke'
    : {'view': True, 'header': 'Относительный перепад давления π на последней решетке', 'dimension': 'МПа',
       'comment': 'Параметры потока в дроссельном блоке', 'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=(O38^((O34-1)/2))/(O30^(1/O34))', 'cell': 'O42'}, 'accuracy': 4},
    'stupeni_n1'
    : {'view': True, 'header': '№ ступени n1', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': 1, 'cell': 'O45'}, 'accuracy': 4},
    'perepad_davlenij_n1'
    : {'view': True, 'header': 'Перепад давлений n1', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {
           'expr': '=IF($O$34=1,$O$42,IF($O$34=2,O50/$O$38^($O$34-O45),IF($O$34=3,O54/$O$38^($O$34-O45),IF($O$34=4,O58/$O$34^($O$34-O45),IF($O$34=5,O62/$O$34^($O$34-O45),IF($O$34=6,O66/$O$34^($O$34-O45),IF($O$34=7,O70/$O$34^($O$34-O45),IF($O$34=8,O74/$O$34^($O$34-O45),IF($O$34=9,O78/$O$34^($O$34-O45),IF($O$34=10,O82/$O$34^($O$34-O45)))))))))))',
           'cell': 'O46'}, 'accuracy': 4},
    'gazodinamicheskaya_funkciya_rashoda_q_n1'
    : {'view': True, 'header': 'Газодинамическая функция расхода, q N1', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {
           'expr': '=IF(O46^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O46^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O46^(($O$31-1)/$O$31))),1)',
           'cell': 'O47'}, 'accuracy': 4},
    'oblast_n1'
    : {'view': True, 'header': 'область N1', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF(AND(O46<1,O46>O144),"Дозвуковая область","Сверхзвуковая область")', 'cell': 'O48'},
       'accuracy': 4},
    'stupeni_n2'
    : {'view': True, 'header': '№ ступени N2', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF($E$17>1,"2","")', 'cell': 'O49'}, 'accuracy': 4},
    'perepad_davlenij_n2'
    : {'view': True, 'header': 'Перепад давлений N2', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {
           'expr': '=IF(O34=1,"",IF(O34=2,O42,IF(O34=3,O54/(O38^(O34-O49)),IF(O34=4,O58/(O38^(O34-O49)),IF(O34=5,O62/(O38^(O34-O49)),IF(O34=6,O66/(O38^(O34-O49)),IF(O34=7,O70/(O38^(O34-O49)),IF(O34=8,O74/(O38^(O34-O49)),IF(O34=9,O78/(O38^(O34-O49)),IF(O34=10,O82/(O38^(O34-O49))))))))))))',
           'cell': 'O50'}, 'accuracy': 4},
    'gazodinamicheskaya_funkciya_rashoda_q_n2'
    : {'view': True, 'header': 'Газодинамическая функция расхода, q N2', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {
           'expr': '=IF(O34=1,"",IF(O50^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O50^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O50^(($O$31-1)/$O$31))),1))',
           'cell': 'O51'}, 'accuracy': 4},
    'oblast_n2'
    : {'view': True, 'header': 'область N2', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF(O34=1,"",IF(AND(O50<1,O50>O144),"Дозвуковая область","Сверхзвуковая область"))',
                   'cell': 'O52'}, 'accuracy': 4},
    'stupeni_n3'
    : {'view': True, 'header': '№ ступени N3', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF($E$17>2,"3","")', 'cell': 'O53'}, 'accuracy': 4},
    'perepad_davlenij_n3'
    : {'view': True, 'header': 'Перепад давлений N3', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {
           'expr': '=IF(O34<3,"",IF(O34=3,O42,IF(O34=4,O58/(O38^(O34-O53)),IF(O34=5,O62/(O38^(O34-O53)),IF(O34=6,O66/(O38^(O34-O53)),IF(O34=7,O70/(O38^(O34-O53)),IF(O34=8,O74/(O38^(O34-O53)),IF(O34=9,O78/(O38^(O34-O53)),IF(O34=10,O82/(O38^(O34-O53)))))))))))',
           'cell': 'O54'}, 'accuracy': 4},
    'gazodinamicheskaya_funkciya_rashoda_q_n3'
    : {'view': True, 'header': 'Газодинамическая функция расхода, q N3', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {
           'expr': '=IF(O34>2,IF(O54^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O54^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O54^(($O$31-1)/$O$31))),1),"")',
           'cell': 'O55'}, 'accuracy': 4},
    'oblast_n3'
    : {'view': True, 'header': 'область N3', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF(O34<3,"",IF(AND(O54<1,O54>O144),"Дозвуковая область","Сверхзвуковая область"))',
                   'cell': 'O56'}, 'accuracy': 4},
    'stupeni_n4'
    : {'view': True, 'header': '№ ступени N4', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF($E$17>3,"4","")', 'cell': 'O57'}, 'accuracy': 4},
    'perepad_davlenij_n4'
    : {'view': True, 'header': 'Перепад давлений N4', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {
           'expr': '=IF($O$34=4,$O$42,IF($O$34<4,"",IF($O$34=5,O62/$O$38^($O$34-O57),IF($O$34=6,O66/$O$38^($O$34-O57),IF($O$34=7,O70/$O$38^($O$34-O57),IF($O$34=8,O74/$O$38^($O$34-O57),IF($O$34=9,O78/$O$38^($O$34-O57),IF($O$34=10,O82/$O$38^($O$34-O57)))))))))',
           'cell': 'O58'}, 'accuracy': 4},
    'gazodinamicheskaya_funkciya_rashoda_q_n4'
    : {'view': True, 'header': 'Газодинамическая функция расхода, q N4', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {
           'expr': '=IF($O$34>3,IF(O58^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O58^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O58^(($O$31-1)/$O$31))),1),"")',
           'cell': 'O59'}, 'accuracy': 4},
    'oblast_n4'
    : {'view': True, 'header': 'область N4', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF(E17>3,IF(AND(O58<1,O58>O144),"Дозвуковая область","Сверхзвуковая область"),"")',
                   'cell': 'O60'}, 'accuracy': 4},
    'stupeni_n5'
    : {'view': True, 'header': '№ ступени N5', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF($E$17>4,5,"")', 'cell': 'O61'}, 'accuracy': 4},
    'perepad_davlenij_n5'
    : {'view': True, 'header': 'Перепад давлений N5', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {
           'expr': '=IF($O$34=5,$O$42,IF($O$34<5,"",IF($O$34=6,O66/$O$38^($O$34-O61),IF($O$34=7,O70/$O$38^($O$34-O61),IF($O$34=8,O74/$O$38^($O$34-O61),IF($O$34=9,O78/$O$38^($O$34-O61),IF($O$34=10,O82/$O$38^($O$34-O61))))))))',
           'cell': 'O62'}, 'accuracy': 4},
    'gazodinamicheskaya_funkciya_rashoda_q_n5'
    : {'view': True, 'header': 'Газодинамическая функция расхода, q N5', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {
           'expr': '=IF($O$34>4,IF(O62^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O62^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O62^(($O$31-1)/$O$31))),1),"")',
           'cell': 'O63'}, 'accuracy': 4},
    'oblast_n5'
    : {'view': True, 'header': 'область N5', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF($E$17>4,IF(AND(O58<1,O58>$O$144),"Дозвуковая область","Сверхзвуковая область"),"")',
                   'cell': 'O64'}, 'accuracy': 4},
    'stupeni_n6'
    : {'view': True, 'header': '№ ступени N6', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF($E$17>5,6,"")', 'cell': 'O65'}, 'accuracy': 4},
    'perepad_davlenij_n6'
    : {'view': True, 'header': 'Перепад давлений N6', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {
           'expr': '=IF($O$34=6,$O$42,IF($O$34<6,"",IF($O$34=7,O70/$O$38^($O$34-O65),IF($O$34=8,O74/$O$38^($O$34-O65),IF($O$34=9,O78/$O$38^($O$34-O65),IF($O$34=10,O82/$O$38^($O$34-O65)))))))',
           'cell': 'O66'}, 'accuracy': 4},
    'gazodinamicheskaya_funkciya_rashoda_q_n6'
    : {'view': True, 'header': 'Газодинамическая функция расхода, q N6', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {
           'expr': '=IF($O$34>5,IF(O66^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O66^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O66^(($O$31-1)/$O$31))),1),"")',
           'cell': 'O67'}, 'accuracy': 4},
    'oblast_n6'
    : {'view': True, 'header': 'область N6', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF($E$17>5,IF(AND(O62<1,O62>$O$144),"Дозвуковая область","Сверхзвуковая область"),"")',
                   'cell': 'O68'}, 'accuracy': 4},
    'stupeni_n7'
    : {'view': True, 'header': '№ ступени N7', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF($E$17>6,7,"")', 'cell': 'O69'}, 'accuracy': 4},
    'perepad_davlenij_n7'
    : {'view': True, 'header': 'Перепад давлений N7', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {
           'expr': '=IF($O$34=7,$O$42,IF($O$34<7,"",IF($O$34=8,O74/$O$38^($O$34-O69),IF($O$34=9,O78/$O$38^($O$34-O69),IF($O$34=10,O82/$O$38^($O$34-O69))))))',
           'cell': 'O70'}, 'accuracy': 4},
    'gazodinamicheskaya_funkciya_rashoda_q_n7'
    : {'view': True, 'header': 'Газодинамическая функция расхода, q N7', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {
           'expr': '=IF($O$34>6,IF(O70^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O70^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O70^(($O$31-1)/$O$31))),1),"")',
           'cell': 'O71'}, 'accuracy': 4},
    'oblast_n7'
    : {'view': True, 'header': 'область N7', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF($E$17>6,IF(AND(O66<1,O66>$O$144),"Дозвуковая область","Сверхзвуковая область"),"")',
                   'cell': 'O72'}, 'accuracy': 4},
    'stupeni_n8'
    : {'view': True, 'header': '№ ступени N8', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF($E$17>7,8,"")', 'cell': 'O73'}, 'accuracy': 4},
    'perepad_davlenij_n8'
    : {'view': True, 'header': 'Перепад давлений N8', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {
           'expr': '=IF($O$34=8,$O$42,IF($O$34<8,"",IF($O$34=9,O78/$O$38^($O$34-O73),IF($O$34=10,O82/$O$38^($O$34-O73)))))',
           'cell': 'O74'}, 'accuracy': 4},
    'gazodinamicheskaya_funkciya_rashoda_q_n8'
    : {'view': True, 'header': 'Газодинамическая функция расхода, q N8', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {
           'expr': '=IF($O$34>7,IF(O74^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O74^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O74^(($O$31-1)/$O$31))),1),"")',
           'cell': 'O75'}, 'accuracy': 4},
    'oblast_n8'
    : {'view': True, 'header': 'область N8', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF($E$17>7,IF(AND(O70<1,O70>$O$144),"Дозвуковая область","Сверхзвуковая область"),"")',
                   'cell': 'O76'}, 'accuracy': 4},
    'stupeni_n9'
    : {'view': True, 'header': '№ ступени N9', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF($E$17>8,9,"")', 'cell': 'O77'}, 'accuracy': 4},
    'perepad_davlenij_n9'
    : {'view': True, 'header': 'Перепад давлений N9', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF($O$34=9,$O$42,IF($O$34<9,"",IF($O$34=10,O82/$O$38^($O$34-O77))))', 'cell': 'O78'},
       'accuracy': 4},
    'gazodinamicheskaya_funkciya_rashoda_q_n9'
    : {'view': True, 'header': 'Газодинамическая функция расхода, q N9', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {
           'expr': '=IF($O$34>8,IF(O78^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O78^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O78^(($O$31-1)/$O$31))),1),"")',
           'cell': 'O79'}, 'accuracy': 4},
    'oblast_n9'
    : {'view': True, 'header': 'область N9', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF($E$17>8,IF(AND(O74<1,O74>$O$144),"Дозвуковая область","Сверхзвуковая область"),"")',
                   'cell': 'O80'}, 'accuracy': 4},
    'stupeni_n10'
    : {'view': True, 'header': '№ ступени N10', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF($E$17>9,10,"")', 'cell': 'O81'}, 'accuracy': 4},
    'perepad_davlenij_n10'
    : {'view': True, 'header': 'Перепад давлений N10', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF($O$34=10,$O$42,IF($O$34<10,""))', 'cell': 'O82'}, 'accuracy': 4},
    'gazodinamicheskaya_funkciya_rashoda_q_n10'
    : {'view': True, 'header': 'Газодинамическая функция расхода, q N10', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {
           'expr': '=IF($O$34>9,IF(O82^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O82^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O82^(($O$31-1)/$O$31))),1),"")',
           'cell': 'O83'}, 'accuracy': 4},
    'oblast_n10'
    : {'view': True, 'header': 'область N10', 'dimension': '', 'comment': '',
       'group_name': 'Параметры потока в дроссельном блоке',
       'formula': {'expr': '=IF($E$17>9,IF(AND(O78<1,O78>$O$144),"Дозвуковая область","Сверхзвуковая область"),"")',
                   'cell': 'O84'}, 'accuracy': 4},
    'stupenin1_2_n1'
    : {'view': True, 'header': '№ ступени N1', 'dimension': '', 'comment': 'Расчет геометрических параметров',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': 1, 'cell': 'O90'}, 'accuracy': 4},
    'diametry_otverstij_mm_n1'
    : {'view': True, 'header': 'Диаметры отверстий, мм N1', 'dimension': 'мм', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=SQRT(4*O92/(0.8*PI()*$O$35))', 'cell': 'O91'}, 'accuracy': 4},
    'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n1'
    : {'view': False, 'header': 'Проходные площади дроссельных решеток Fi, мм2 N1', 'dimension': 'м2', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=($O$31+1)/(2*$O$31)*O24*O28/(O26*O47*(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))',
                   'cell': 'O92'}, 'accuracy': 4},
    'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n1'
    : {'view': False,
       'header': '\nМинимальные площади дроссельных решеток, требуемые для размещения отверстий Fтр, мм2 N1',
       'dimension': 'м2', 'comment': '', 'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=5*O92/0.8', 'cell': 'O93'}, 'accuracy': 4},
    'stupenin1_2_n2'
    : {'view': True, 'header': '№ ступени N2', 'dimension': '', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF(O34=1,"",2)', 'cell': 'O94'}, 'accuracy': 4},
    'diametry_otverstij_mm_n2'
    : {'view': True, 'header': 'Диаметры отверстий, мм N2', 'dimension': 'мм', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF(O34=1,"",SQRT(4*O96/(0.8*PI()*$O$35)))', 'cell': 'O95'}, 'accuracy': 4},
    'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n2'
    : {'view': False, 'header': 'Проходные площади дроссельных решеток Fi, мм2 N2', 'dimension': 'м2', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF($O$34=1,"",O92*O47*$O$42*$O$38^-$O$34/(($O$42*$O$38^((O94-1)/2-$O$34))^O94*O51))',
                   'cell': 'O96'}, 'accuracy': 4},
    'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n2'
    : {'view': False,
       'header': '\nМинимальные площади дроссельных решеток, требуемые для размещения отверстий Fтр, мм2 N2',
       'dimension': 'м2', 'comment': '', 'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF(O34=1,"",5*O96/0.8)', 'cell': 'O97'}, 'accuracy': 4},
    'stupenin1_2_n3'
    : {'view': True, 'header': '№ ступени N3', 'dimension': '', 'comment': '№ ступени N3',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF(O34<3,"",3)', 'cell': 'O98'}, 'accuracy': 4},
    'diametry_otverstij_mm_n3'
    : {'view': True, 'header': 'Диаметры отверстий, мм N3', 'dimension': 'мм', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF(O34<3,"",SQRT(4*O100/(0.8*PI()*$O$35)))', 'cell': 'O99'}, 'accuracy': 4},
    'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n3'
    : {'view': False, 'header': 'Проходные площади дроссельных решеток Fi, мм2 N3', 'dimension': 'м2', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF(O34<3,"",O92*O47*O42*O38^-O34/((O42*O38^((O98-1)/2-O34))^O98*O55))', 'cell': 'O100'},
       'accuracy': 4},
    'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n3'
    : {'view': False,
       'header': '\nМинимальные площади дроссельных решеток, требуемые для размещения отверстий Fтр, мм2 N3',
       'dimension': 'м2', 'comment': '', 'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF(O34<3,"",5*O100/0.8)', 'cell': 'O101'}, 'accuracy': 4},
    'stupenin1_2_n4'
    : {'view': True, 'header': '№ ступени N4', 'dimension': '', 'comment': '№ ступени N4',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF(O34<4,"",4)', 'cell': 'O102'}, 'accuracy': 4},
    'diametry_otverstij_mm_n4'
    : {'view': True, 'header': 'Диаметры отверстий, мм N4', 'dimension': 'мм', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF(O34<4,"",SQRT(4*O104/(0.8*PI()*$O$35)))', 'cell': 'O103'}, 'accuracy': 4},
    'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n4'
    : {'view': False, 'header': 'Проходные площади дроссельных решеток Fi, мм2 N4', 'dimension': 'м2', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF(O34<4,"",O92*O47*O42*O38^-O34/((O42*O38^((O102-1)/2-O34))^O102*O59))', 'cell': 'O104'},
       'accuracy': 4},
    'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n4'
    : {'view': False,
       'header': '\nМинимальные площади дроссельных решеток, требуемые для размещения отверстий Fтр, мм2 N4',
       'dimension': 'м2', 'comment': '', 'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF(O34<4,"",5*O104/0.8)', 'cell': 'O105'}, 'accuracy': 4},
    'stupenin1_2_n5'
    : {'view': True, 'header': '№ ступени N5', 'dimension': '', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF($O$34<5,"",5)', 'cell': 'O106'}, 'accuracy': 4},
    'diametry_otverstij_mm_n5'
    : {'view': True, 'header': 'Диаметры отверстий, мм N5', 'dimension': 'мм', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF($O$34<5,"",SQRT(4*O108/(0.8*PI()*$O$35)))', 'cell': 'O107'}, 'accuracy': 4},
    'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n5'
    : {'view': False, 'header': 'Проходные площади дроссельных решеток Fi, мм2 N5', 'dimension': 'м2', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF(O34<5,"",$O$92*O47*$O$42*$O$38^-$O$34/(($O$42*$O$38^((O106-1)/2-$O$34))^O106*O63))',
                   'cell': 'O108'}, 'accuracy': 4},
    'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n5'
    : {'view': False,
       'header': '\nМинимальные площади дроссельных решеток, требуемые для размещения отверстий Fтр, мм2 N5',
       'dimension': 'м2', 'comment': '', 'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF($O$34<5,"",5*O108/0.8)', 'cell': 'O109'}, 'accuracy': 4},
    'stupenin1_2_n6'
    : {'view': True, 'header': '№ ступени N6', 'dimension': '', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF($O$34<6,"",6)', 'cell': 'O110'}, 'accuracy': 4},
    'diametry_otverstij_mm_n6'
    : {'view': True, 'header': 'Диаметры отверстий, мм N6', 'dimension': 'мм', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF($O$34<6,"",SQRT(4*O112/(0.8*PI()*$O$35)))', 'cell': 'O111'}, 'accuracy': 4},
    'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n6'
    : {'view': False, 'header': 'Проходные площади дроссельных решеток Fi, мм2 N6', 'dimension': 'м2', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF(O34<6,"",$O$92*O47*$O$42*$O$38^-$O$34/(($O$42*$O$38^((O110-1)/2-$O$34))^O110*O67))',
                   'cell': 'O112'}, 'accuracy': 4},
    'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n6'
    : {'view': False,
       'header': '\nМинимальные площади дроссельных решеток, требуемые для размещения отверстий Fтр, мм2 N6',
       'dimension': 'м2', 'comment': '', 'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF($O$34<6,"",5*O112/0.8)', 'cell': 'O113'}, 'accuracy': 4},
    'stupenin1_2_n7'
    : {'view': True, 'header': '№ ступени N7', 'dimension': '', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF($O$34<7,"",7)', 'cell': 'O114'}, 'accuracy': 4},
    'diametry_otverstij_mm_n7'
    : {'view': True, 'header': 'Диаметры отверстий, мм N7', 'dimension': 'мм', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF($O$34<7,"",SQRT(4*O116/(0.8*PI()*$O$35)))', 'cell': 'O115'}, 'accuracy': 4},
    'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n7'
    : {'view': False, 'header': 'Проходные площади дроссельных решеток Fi, мм2 N7', 'dimension': 'м2', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF(O34<7,"",$O$92*O47*$O$42*$O$38^-$O$34/(($O$42*$O$38^((O114-1)/2-$O$34))^O114*O71))',
                   'cell': 'O116'}, 'accuracy': 4},
    'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n7'
    : {'view': False,
       'header': '\nМинимальные площади дроссельных решеток, требуемые для размещения отверстий Fтр, мм2 N7',
       'dimension': 'м2', 'comment': '', 'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF($O$34<7,"",5*O116/0.8)', 'cell': 'O117'}, 'accuracy': 4},
    'stupenin1_2_n8'
    : {'view': True, 'header': '№ ступени N8', 'dimension': '', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF($O$34<8,"",8)', 'cell': 'O118'}, 'accuracy': 4},
    'diametry_otverstij_mm_n8'
    : {'view': True, 'header': 'Диаметры отверстий, мм N8', 'dimension': 'мм', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF($O$34<8,"",SQRT(4*O120/(0.8*PI()*$O$35)))', 'cell': 'O119'}, 'accuracy': 4},
    'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n8'
    : {'view': False, 'header': 'Проходные площади дроссельных решеток Fi, мм2 N8', 'dimension': 'м2', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF(O34<8,"",$O$92*O47*$O$42*$O$38^-$O$34/(($O$42*$O$38^((O118-1)/2-$O$34))^O118*O75))',
                   'cell': 'O120'}, 'accuracy': 4},
    'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n8'
    : {'view': False,
       'header': '\nМинимальные площади дроссельных решеток, требуемые для размещения отверстий Fтр, мм2 N8',
       'dimension': 'м2', 'comment': '', 'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF($O$34<8,"",5*O120/0.8)', 'cell': 'O121'}, 'accuracy': 4},
    'stupenin1_2_n9'
    : {'view': True, 'header': '№ ступени N9', 'dimension': '', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF($O$34<9,"",9)', 'cell': 'O122'}, 'accuracy': 4},
    'diametry_otverstij_mm_n9'
    : {'view': True, 'header': 'Диаметры отверстий, мм N9', 'dimension': 'мм', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF($O$34<9,"",SQRT(4*O124/(0.8*PI()*$O$35)))', 'cell': 'O123'}, 'accuracy': 4},
    'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n9'
    : {'view': False, 'header': 'Проходные площади дроссельных решеток Fi, мм2 N9', 'dimension': 'м2', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF(O34<9,"",$O$92*O47*$O$42*$O$38^-$O$34/(($O$42*$O$38^((O122-1)/2-$O$34))^O122*O79))',
                   'cell': 'O124'}, 'accuracy': 4},
    'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n9'
    : {'view': False,
       'header': '\nМинимальные площади дроссельных решеток, требуемые для размещения отверстий Fтр, мм2 N9',
       'dimension': 'м2', 'comment': '', 'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF($O$34<9,"",5*O124/0.8)', 'cell': 'O125'}, 'accuracy': 4},
    'stupenin1_2_n10'
    : {'view': True, 'header': '№ ступени N10', 'dimension': '', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF($O$34<10,"",10)', 'cell': 'O126'}, 'accuracy': 4},
    'diametry_otverstij_mm_n10'
    : {'view': True, 'header': 'Диаметры отверстий, мм N10', 'dimension': 'мм', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF($O$34<10,"",SQRT(4*O128/(0.8*PI()*$O$35)))', 'cell': 'O127'}, 'accuracy': 4},
    'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n10'
    : {'view': False, 'header': 'Проходные площади дроссельных решеток Fi, мм2 N10', 'dimension': 'м2', 'comment': '',
       'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF(O34<10,"",$O$92*O47*$O$42*$O$38^-$O$34/(($O$42*$O$38^((O126-1)/2-$O$34))^O126*O83))',
                   'cell': 'O128'}, 'accuracy': 4},
    'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n10'
    : {'view': False,
       'header': '\nМинимальные площади дроссельных решеток, требуемые для размещения отверстий Fтр, мм2 N10',
       'dimension': 'м2', 'comment': '', 'group_name': 'Расчет геометрических параметров',
       'formula': {'expr': '=IF($O$34<10,"",5*O128/0.8)', 'cell': 'O129'}, 'accuracy': 4},
    'temperatura_k'
    : {'view': True, 'header': 'Температура, К', 'dimension': '°С', 'comment': '', 'group_name': 'Аэродинамика',
       'formula': {'expr': '=O25+273.15', 'cell': 'O135'}, 'accuracy': 4},
    'sa_ploschad_secheniya_shumoglushitelya_m2'
    : {'view': True, 'header': 'Sa - Площадь сечения шумоглушителя, м2', 'dimension': 'м2', 'comment': '',
       'group_name': 'Аэродинамика',
       'formula': {'expr': '=PI()*O139^2/4', 'cell': 'O136'}, 'accuracy': 4},
    'perimetr_m'
    : {'view': True, 'header': 'Периметр, м', 'dimension': 'м', 'comment': '', 'group_name': 'Аэродинамика',
       'formula': {'expr': '=PI()*E27', 'cell': 'O137'}, 'accuracy': 4},
    'sk_ploschad_vyhodnogo_secheniya_korpusa_do_kryshki_kv_m'
    : {'view': True, 'header': 'Sk -  Площадь выходного сечения корпуса до крышки, кв.м', 'dimension': 'м2',
       'comment': '',
       'group_name': 'Аэродинамика',
       'formula': {'expr': '=PI()*E27*E35', 'cell': 'O138'}, 'accuracy': 4},
    'da_vnutrennij_diametr_vyhlopa_iz_korpusa_m'
    : {'view': True, 'header': 'Da - Внутренний диаметр выхлопа из корпуса, м', 'dimension': 'м', 'comment': '',
       'group_name': 'Аэродинамика',
       'formula': {'expr': '=E27-2*E28', 'cell': 'O139'}, 'accuracy': 4},
    'nezapolnennaya_ploschad_kv_m'
    : {'view': True, 'header': 'Незаполненная площадь, кв.м.', 'dimension': 'м2', 'comment': '',
       'group_name': 'Аэродинамика',
       'formula': {'expr': '=O136-E33', 'cell': 'O140'}, 'accuracy': 4},
    'gidravlicheskij_diametr_m'
    : {'view': True, 'header': 'Гидравлический диаметр, м', 'dimension': 'м', 'comment': '',
       'group_name': 'Аэродинамика',
       'formula': {'expr': '=4*O140/E34', 'cell': 'O141'}, 'accuracy': 4},
    'otnositelnaya_ploschad'
    : {'view': True, 'header': 'Относительная площадь', 'dimension': 'м2', 'comment': '', 'group_name': 'Аэродинамика',
       'formula': {'expr': '=O140/O136', 'cell': 'O142'}, 'accuracy': 4},
    'pd_srednij_skorostnoj_napor_na_vyhode_iz_schelevyh_kanalov'
    : {'view': True, 'header': 'Pd - Средний скоростной напор на выходе из щелевых каналов', 'dimension': 'м/с',
       'comment': '',
       'group_name': 'Аэродинамика',
       'formula': {'expr': '=MAX(O318,O333,O348,O363,O378,O393)', 'cell': 'O143'}, 'accuracy': 4},
    'kriticheskij_perepad_davlenij'
    : {'view': True, 'header': 'Критический перепад давлений', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Аэродинамика',
       'formula': {'expr': '=(2/($O$31+1))^($O$31/($O$31-1))', 'cell': 'O144'}, 'accuracy': 4},
    'pk_izbytochnoe_davlenie_pod_kryshkoj_pa'
    : {'view': True, 'header': 'Pk - Избыточное давление под крышкой, Па', 'dimension': 'Па',
       'comment': 'Расчет давлений',
       'group_name': 'Расчет давлений',
       'formula': {'expr': '=O284', 'cell': 'O150'}, 'accuracy': 4},
    'pa_izbytochnoe_davlenie_na_vyhode_iz_korpusa_za_stupenyu_zvukopogloscheniya_pa'
    : {'view': True, 'header': 'Pa - Избыточное давление на выходе из корпуса за ступенью звукопоглощения, Па',
       'dimension': 'Па',
       'comment': '', 'group_name': 'Расчет давлений',
       'formula': {'expr': '=O285', 'cell': 'O151'}, 'accuracy': 4},
    'pa_absolyutnoe_davlenie_za_stupenyu_zvukopogloscheniya_pa'
    : {'view': True, 'header': 'pa - Абсолютное давление за ступенью звукопоглощения, Па', 'dimension': 'Па',
       'comment': '',
       'group_name': 'Расчет давлений',
       'formula': {'expr': '=O286', 'cell': 'O152'}, 'accuracy': 4},
    'pi3_davlenie_pered_stupenyu_zvukopogloscheniya_pa'
    : {'view': True, 'header': 'pi3 - Давление перед ступенью звукопоглощения, Па', 'dimension': 'Па', 'comment': '',
       'group_name': 'Расчет давлений',
       'formula': {'expr': '=O267', 'cell': 'O153'}, 'accuracy': 4},
    'izbytochnoe_davlenie_pod_kryshkoj_ne_mozhet_prevyshat_15000_pa'
    : {'view': True, 'header': 'Избыточное давление под крышкой, Не может превышать 15000 Па', 'dimension': 'Па',
       'comment': '',
       'group_name': 'Расчет давлений',
       'formula': {'expr': '=IF(O150>=0.15*10^5,"ОШИБКА","")', 'cell': 'O154'}, 'accuracy': 4},
    'izbytochnoe_davlenie_na_vyhode_iz_korpusa_za_stupenyu_zvukopogloscheniya_ne_mozhet_prevyshat_15000_pa'
    : {'view': True,
       'header': 'Избыточное давление на выходе из корпуса за ступенью звукопоглощения, Не может превышать 15000 Па',
       'dimension': 'Па', 'comment': '', 'group_name': 'Расчет давлений',
       'formula': {'expr': '=IF(O151>=0.15*10^5,"ОШИБКА","")', 'cell': 'O155'}, 'accuracy': 4},
    'wa_skorost_na_vyhode_iz_korpusa_m_s'
    : {'view': True, 'header': 'wa - Скорость на выходе из корпуса, м/с', 'dimension': 'м/с',
       'comment': 'Расчет скоростей',
       'group_name': 'Расчет скоростей',
       'formula': {'expr': '=O291', 'cell': 'O161'}, 'accuracy': 4},
    'wk_skorost_na_vyhlope_v_atmosferu_m_s'
    : {'view': True, 'header': 'wk - Скорость на выхлопе в атмосферу, м/с', 'dimension': 'м/с', 'comment': '',
       'group_name': 'Расчет скоростей',
       'formula': {'expr': '=O292', 'cell': 'O162'}, 'accuracy': 4},
    'ma_chislo_maha_na_vyhode_iz_korpusa'
    : {'view': True, 'header': 'Ma - Число Маха на выходе из корпуса', 'dimension': '', 'comment': '',
       'group_name': 'Расчет скоростей',
       'formula': {'expr': '=O293', 'cell': 'O163'}, 'accuracy': 4},
    'mk_chislo_maha_na_vyhlope_v_atmosferu'
    : {'view': True, 'header': 'Mk - Число Маха на выхлопе в атмосферу', 'dimension': '', 'comment': '',
       'group_name': 'Расчет скоростей',
       'formula': {'expr': '=O294', 'cell': 'O164'}, 'accuracy': 4},
    'dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_bokovom_vyhlope_kn'
    : {'view': True, 'header': 'Динамическая нагрузка на защитную крышку при боковом выхлопе, кН', 'dimension': '',
       'comment': 'Динамические нагрузки', 'group_name': 'Динамические нагрузки',
       'formula': {'expr': '=O306', 'cell': 'O168'}, 'accuracy': 4},
    'dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_osevom_vyhlope_kn'
    : {'view': True, 'header': 'Динамическая нагрузка на защитную крышку при осевом выхлопе, кН', 'dimension': '',
       'comment': '',
       'group_name': 'Динамические нагрузки',
       'formula': {'expr': '=O307', 'cell': 'O169'}, 'accuracy': 4},
    'dinamicheskaya_nagruzka_na_drosselnyj_blok_kn'
    : {'view': True, 'header': 'Динамическая нагрузка на дроссельный блок, кН', 'dimension': '', 'comment': '',
       'group_name': 'Динамические нагрузки',
       'formula': {'expr': '=O304', 'cell': 'O170'}, 'accuracy': 4},
    'dinamicheskaya_nagruzka_na_stupen_zvukopogloscheniya_kn'
    : {'view': True, 'header': 'Динамическая нагрузка на ступень звукопоглощения, кН', 'dimension': '', 'comment': '',
       'group_name': 'Динамические нагрузки',
       'formula': {'expr': '=O305', 'cell': 'O171'}, 'accuracy': 4},
    'stupeni_n0'
    : {'view': True, 'header': '№ ступени N0', 'dimension': '', 'comment': 'Давление за дроссельными решетками',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=0', 'cell': 'O173'}, 'accuracy': 4},
    'davlenie_za_reshetkami_mpa_n0'
    : {'view': True, 'header': 'Давление за решетками, МПа N0', 'dimension': 'МПа', 'comment': '',
       'formula': {'expr': '=O181/O183', 'cell': 'O174'}, 'accuracy': 4,
       'group_name': 'Давление за дроссельными решетками'},
    'y_n0'
    : {'view': True, 'header': 'y N0', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=0', 'cell': 'O175'}, 'accuracy': 4},
    'perepad_davlenij_n0'
    : {'view': True, 'header': 'π - Перепад давлений N0', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=0', 'cell': 'O176'}, 'accuracy': 4},
    'n0'
    : {'view': True, 'header': 'λ N0', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=0', 'cell': 'O177'}, 'accuracy': 4},
    'n0_2'
    : {'view': True, 'header': 'ε (λ) N0', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=0', 'cell': 'O178'}, 'accuracy': 4},
    'n0_3'
    : {'view': True, 'header': 'τ(λ) N0', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=0', 'cell': 'O179'}, 'accuracy': 4},
    'stupeni_n1_3'
    : {'view': True, 'header': '№ ступени N1', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': 1, 'cell': 'O180'}, 'accuracy': 4},
    'davlenie_za_reshetkami_mpa_n1'
    : {'view': True, 'header': 'Давление за решетками, МПа N1', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(E17=1,O27,O188/O190)', 'cell': 'O181'}, 'accuracy': 4},
    'y_n1'
    : {'view': True, 'header': 'y N1', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=O13/(O92*O181)', 'cell': 'O182'}, 'accuracy': 4},
    'perepad_davlenij_n1_2'
    : {'view': True, 'header': 'π - Перепад давлений N1', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O182>=O14,1/O182,O185*O186)', 'cell': 'O183'}, 'accuracy': 4},
    'n1'
    : {'view': True, 'header': 'λ N1', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=(-1+(1+4*(($O$31-1)/($O$31+1))*O12^2*O182^2)^0.5)/(2*(($O$31-1)/($O$31+1))*O12*O182)',
                   'cell': 'O184'}, 'accuracy': 4},
    'n1_2'
    : {'view': True, 'header': 'ε (λ) N1', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=(1-(($O$31-1)/($O$31+1))*O184^2)^(1/($O$31-1))', 'cell': 'O185'}, 'accuracy': 4},
    'n1_3'
    : {'view': True, 'header': 'τ(λ) N1', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=1-(($O$31-1)/($O$31+1))*O184^2', 'cell': 'O186'}, 'accuracy': 4},
    'stupeni_n2_3'
    : {'view': True, 'header': '№ ступени N2', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF($O$34>1,2,"")', 'cell': 'O187'}, 'accuracy': 4},
    'davlenie_za_reshetkami_mpa_n2'
    : {'view': True, 'header': 'Давление за решетками, МПа N2', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O187="","",IF(E17=2,O27,O195/O197))', 'cell': 'O188'}, 'accuracy': 4},
    'y_n2'
    : {'view': True, 'header': 'y N2', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O187="","",O13/(O96*O188))', 'cell': 'O189'}, 'accuracy': 4},
    'perepad_davlenij_n2_2'
    : {'view': True, 'header': 'π - Перепад давлений N2', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O187="","",IF(O189>=O14,1/O189,O192*O193))', 'cell': 'O190'}, 'accuracy': 4},
    'n2'
    : {'view': True, 'header': 'λ N2', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {
           'expr': '=IF(O187="","",(-1+(1+4*(($O$31-1)/($O$31+1))*O12^2*O189^2)^0.5)/(2*(($O$31-1)/($O$31+1))*O12*O189))',
           'cell': 'O191'}, 'accuracy': 4},
    'n2_2'
    : {'view': True, 'header': 'ε (λ) N2', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O187="","",(1-(($O$31-1)/($O$31+1))*O191^2)^(1/($O$31-1)))', 'cell': 'O192'},
       'accuracy': 4},
    'n2_3'
    : {'view': True, 'header': 'τ(λ) N2', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O187="","",1-(($O$31-1)/($O$31+1))*O191^2)', 'cell': 'O193'}, 'accuracy': 4},
    'stupeni_n3_3'
    : {'view': True, 'header': '№ ступени N3', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF($O$34>2,3,"")', 'cell': 'O194'}, 'accuracy': 4},
    'davlenie_za_reshetkami_mpa_n3'
    : {'view': True, 'header': 'Давление за решетками, МПа N3', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O194="","",IF(E17=3,O27,O202/O204))', 'cell': 'O195'}, 'accuracy': 4},
    'y_n3'
    : {'view': True, 'header': 'y N3', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O194="","",O13/(O100*O195))', 'cell': 'O196'}, 'accuracy': 4},
    'perepad_davlenij_n3_2'
    : {'view': True, 'header': 'π - Перепад давлений N3', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O194="","",IF(O196>=O14,1/O196,O199*O200))', 'cell': 'O197'}, 'accuracy': 4},
    'n3'
    : {'view': True, 'header': 'λ N3', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {
           'expr': '=IF(O194="","",(-1+(1+4*(($O$31-1)/($O$31+1))*O12^2*O196^2)^0.5)/(2*(($O$31-1)/($O$31+1))*O12*O196))',
           'cell': 'O198'}, 'accuracy': 4},
    'n3_2'
    : {'view': True, 'header': 'ε (λ) N3', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O194="","",(1-(($O$31-1)/($O$31+1))*O198^2)^(1/($O$31-1)))', 'cell': 'O199'},
       'accuracy': 4},
    'n3_3'
    : {'view': True, 'header': 'τ(λ) N3', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O194="","",1-(($O$31-1)/($O$31+1))*O198^2)', 'cell': 'O200'}, 'accuracy': 4},
    'stupeni_n4_3'
    : {'view': True, 'header': '№ ступени N4', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF($E$17>3,4,"")', 'cell': 'O201'}, 'accuracy': 4},
    'davlenie_za_reshetkami_mpa_n4'
    : {'view': True, 'header': 'Давление за решетками, МПа N4', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O201="","",IF($E$17=4,$O$27,O209/O211))', 'cell': 'O202'}, 'accuracy': 4},
    'y_n4'
    : {'view': True, 'header': 'y N4', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O201="","",O13/(O104*O202))', 'cell': 'O203'}, 'accuracy': 4},
    'perepad_davlenij_n4_2'
    : {'view': True, 'header': 'π - Перепад давлений N4', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O201="","",IF(O203>=O14,1/O203,O206*O207))', 'cell': 'O204'}, 'accuracy': 4},
    'n4'
    : {'view': True, 'header': 'λ N4', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {
           'expr': '=IF(O201="","",(-1+(1+4*(($O$31-1)/($O$31+1))*O12^2*O203^2)^0.5)/(2*(($O$31-1)/($O$31+1))*O12*O203))',
           'cell': 'O205'}, 'accuracy': 4},
    'n4_2'
    : {'view': True, 'header': 'ε (λ) N4', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O201="","",(1-(($O$31-1)/($O$31+1))*O205^2)^(1/($O$31-1)))', 'cell': 'O206'},
       'accuracy': 4},
    'n4_3'
    : {'view': True, 'header': 'τ(λ) N4', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O201="","",1-(($O$31-1)/($O$31+1))*O205^2)', 'cell': 'O207'}, 'accuracy': 4},
    'stupeni_n5_3'
    : {'view': True, 'header': '№ ступени N5', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF($E$17>4,5,"")', 'cell': 'O208'}, 'accuracy': 4},
    'davlenie_za_reshetkami_mpa_n5'
    : {'view': True, 'header': 'Давление за решетками, МПа N5', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O208="","",IF($E$17=5,$O$27,O216/O218))', 'cell': 'O209'}, 'accuracy': 4},
    'y_n5'
    : {'view': True, 'header': 'y N5', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O208="","",$O$13/(O108*O209))', 'cell': 'O210'}, 'accuracy': 4},
    'perepad_davlenij_n5_2'
    : {'view': True, 'header': 'π - Перепад давлений N5', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O208="","",IF(O210>=$O$14,1/O210,O213*O214))', 'cell': 'O211'}, 'accuracy': 4},
    'n5'
    : {'view': True, 'header': 'λ N5', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {
           'expr': '=IF(O208="","",(-1+(1+4*(($O$31-1)/($O$31+1))*$O$12^2*O210^2)^0.5)/(2*(($O$31-1)/($O$31+1))*$O$12*O210))',
           'cell': 'O212'}, 'accuracy': 4},
    'n5_2'
    : {'view': True, 'header': 'ε (λ) N5', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O208="","",(1-(($O$31-1)/($O$31+1))*O212^2)^(1/($O$31-1)))', 'cell': 'O213'},
       'accuracy': 4},
    'n5_3'
    : {'view': True, 'header': 'τ(λ) N5', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O208="","",1-(($O$31-1)/($O$31+1))*O212^2)', 'cell': 'O214'}, 'accuracy': 4},
    'stupeni_n6_3'
    : {'view': True, 'header': '№ ступени N6', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF($E$17>5,6,"")', 'cell': 'O215'}, 'accuracy': 4},
    'davlenie_za_reshetkami_mpa_n6'
    : {'view': True, 'header': 'Давление за решетками, МПа N6', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O215="","",IF($E$17=6,$O$27,O223/O225))', 'cell': 'O216'}, 'accuracy': 4},
    'y_n6'
    : {'view': True, 'header': 'y N6', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O215="","",$O$13/(O112*O216))', 'cell': 'O217'}, 'accuracy': 4},
    'perepad_davlenij_n6_2'
    : {'view': True, 'header': 'π - Перепад давлений N6', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O215="","",IF(O217>=$O$14,1/O217,O220*O221))', 'cell': 'O218'}, 'accuracy': 4},
    'n6'
    : {'view': True, 'header': 'λ N6', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {
           'expr': '=IF(O215="","",(-1+(1+4*(($O$31-1)/($O$31+1))*$O$12^2*O217^2)^0.5)/(2*(($O$31-1)/($O$31+1))*$O$12*O217))',
           'cell': 'O219'}, 'accuracy': 4},
    'n6_2'
    : {'view': True, 'header': 'ε (λ) N6', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O215="","",(1-(($O$31-1)/($O$31+1))*O219^2)^(1/($O$31-1)))', 'cell': 'O220'},
       'accuracy': 4},
    'n6_3'
    : {'view': True, 'header': 'τ(λ) N6', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O215="","",1-(($O$31-1)/($O$31+1))*O219^2)', 'cell': 'O221'}, 'accuracy': 4},
    'stupeni_n7_3'
    : {'view': True, 'header': '№ ступени N7', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF($E$17>6,7,"")', 'cell': 'O222'}, 'accuracy': 4},
    'davlenie_za_reshetkami_mpa_n7'
    : {'view': True, 'header': 'Давление за решетками, МПа N7', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O222="","",IF($E$17=7,$O$27,O230/O232))', 'cell': 'O223'}, 'accuracy': 4},
    'y_n7'
    : {'view': True, 'header': 'y N7', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O222="","",$O$13/(O116*O223))', 'cell': 'O224'}, 'accuracy': 4},
    'perepad_davlenij_n7_2'
    : {'view': True, 'header': 'π - Перепад давлений N7', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O222="","",IF(O224>=$O$14,1/O224,O227*O228))', 'cell': 'O225'}, 'accuracy': 4},
    'n7'
    : {'view': True, 'header': 'λ N7', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {
           'expr': '=IF(O222="","",(-1+(1+4*(($O$31-1)/($O$31+1))*$O$12^2*O224^2)^0.5)/(2*(($O$31-1)/($O$31+1))*$O$12*O224))',
           'cell': 'O226'}, 'accuracy': 4},
    'n7_2'
    : {'view': True, 'header': 'ε (λ) N7', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O222="","",(1-(($O$31-1)/($O$31+1))*O226^2)^(1/($O$31-1)))', 'cell': 'O227'},
       'accuracy': 4},
    'n7_3'
    : {'view': True, 'header': 'τ(λ) N7', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O222="","",1-(($O$31-1)/($O$31+1))*O226^2)', 'cell': 'O228'}, 'accuracy': 4},
    'stupeni_n8_3'
    : {'view': True, 'header': '№ ступени N8', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF($E$17>7,8,"")', 'cell': 'O229'}, 'accuracy': 4},
    'davlenie_za_reshetkami_mpa_n8'
    : {'view': True, 'header': 'Давление за решетками, МПа N8', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O229="","",IF($E$17=8,$O$27,O237/O239))', 'cell': 'O230'}, 'accuracy': 4},
    'y_n8'
    : {'view': True, 'header': 'y N8', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O229="","",$O$13/(O120*O230))', 'cell': 'O231'}, 'accuracy': 4},
    'perepad_davlenij_n8_2'
    : {'view': True, 'header': 'π - Перепад давлений N8', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O229="","",IF(O231>=$O$14,1/O231,O234*O235))', 'cell': 'O232'}, 'accuracy': 4},
    'n8'
    : {'view': True, 'header': 'λ N8', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {
           'expr': '=IF(O229="","",(-1+(1+4*(($O$31-1)/($O$31+1))*$O$12^2*O231^2)^0.5)/(2*(($O$31-1)/($O$31+1))*$O$12*O231))',
           'cell': 'O233'}, 'accuracy': 4},
    'n8_2'
    : {'view': True, 'header': 'ε (λ) N8', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O229="","",(1-(($O$31-1)/($O$31+1))*O233^2)^(1/($O$31-1)))', 'cell': 'O234'},
       'accuracy': 4},
    'n8_3'
    : {'view': True, 'header': 'τ(λ) N8', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O229="","",1-(($O$31-1)/($O$31+1))*O233^2)', 'cell': 'O235'}, 'accuracy': 4},
    'stupeni_n9_3'
    : {'view': True, 'header': '№ ступени N9', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF($E$17>8,9,"")', 'cell': 'O236'}, 'accuracy': 4},
    'davlenie_za_reshetkami_mpa_n9'
    : {'view': True, 'header': 'Давление за решетками, МПа N9', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O236="","",IF($E$17=9,$O$27,O244/O246))', 'cell': 'O237'}, 'accuracy': 4},
    'y_n9'
    : {'view': True, 'header': 'y N9', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O236="","",$O$13/(O124*O237))', 'cell': 'O238'}, 'accuracy': 4},
    'perepad_davlenij_n9_2'
    : {'view': True, 'header': 'π - Перепад давлений N9', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O236="","",IF(O238>=$O$14,1/O238,O241*O242))', 'cell': 'O239'}, 'accuracy': 4},
    'n9'
    : {'view': True, 'header': 'λ N9', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {
           'expr': '=IF(O236="","",(-1+(1+4*(($O$31-1)/($O$31+1))*$O$12^2*O238^2)^0.5)/(2*(($O$31-1)/($O$31+1))*$O$12*O238))',
           'cell': 'O240'}, 'accuracy': 4},
    'n9_2'
    : {'view': True, 'header': 'ε (λ) N9', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O236="","",(1-(($O$31-1)/($O$31+1))*O240^2)^(1/($O$31-1)))', 'cell': 'O241'},
       'accuracy': 4},
    'n9_3'
    : {'view': True, 'header': 'τ(λ) N9', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O236="","",1-(($O$31-1)/($O$31+1))*O240^2)', 'cell': 'O242'}, 'accuracy': 4},
    'stupeni_n10_3'
    : {'view': True, 'header': '№ ступени N10', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF($E$17>9,10,"")', 'cell': 'O243'}, 'accuracy': 4},
    'davlenie_za_reshetkami_mpa_n10'
    : {'view': True, 'header': 'Давление за решетками, МПа N10', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF($O$34<10,"",IF($E$17=10,$O$27))', 'cell': 'O244'}, 'accuracy': 4},
    'y_n10'
    : {'view': True, 'header': 'y N10', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O243="","",$O$13/(O128*O244))', 'cell': 'O245'}, 'accuracy': 4},
    'perepad_davlenij_n10_2'
    : {'view': True, 'header': 'π - Перепад давлений N10', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O243="","",IF(O245>=$O$14,1/O245,O248*O249))', 'cell': 'O246'}, 'accuracy': 4},
    'n10'
    : {'view': True, 'header': 'λ N10', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {
           'expr': '=IF(O243="","",(-1+(1+4*(($O$31-1)/($O$31+1))*$O$12^2*O245^2)^0.5)/(2*(($O$31-1)/($O$31+1))*$O$12*O245))',
           'cell': 'O247'}, 'accuracy': 4},
    'n10_2'
    : {'view': True, 'header': 'ε (λ) N10', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O243="","",(1-(($O$31-1)/($O$31+1))*O247^2)^(1/($O$31-1)))', 'cell': 'O248'},
       'accuracy': 4},
    'n10_3'
    : {'view': True, 'header': 'τ(λ) N10', 'dimension': '', 'comment': '',
       'group_name': 'Давление за дроссельными решетками',
       'formula': {'expr': '=IF(O243="","",1-(($O$31-1)/($O$31+1))*O247^2)', 'cell': 'O249'}, 'accuracy': 4},
    'obtekateli'
    : {'view': True, 'header': 'Обтекатели', 'dimension': '', 'comment': 'Расчет аэродинамики для кольцевых каналов',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=E25', 'cell': 'O253'}, 'accuracy': 4},
    'r_gazovaya_postoyannaya_m2s2_k'
    : {'view': True, 'header': 'R - Газовая постоянная, м2с2/К', 'dimension': '', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=O29', 'cell': 'O254'}, 'accuracy': 4},
    'k_pokazatel_adiabaty'
    : {'view': True, 'header': 'k - Показатель адиабаты', 'dimension': '', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=$O$31', 'cell': 'O255'}, 'accuracy': 4},
    't_absolyutnaya_temperatura_pered_glushitelem_k'
    : {'view': True, 'header': 'Т - Абсолютная температура перед глушителем, К', 'dimension': '°С', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=O135', 'cell': 'O256'}, 'accuracy': 4},
    'g_rashod_sredy_kg_s'
    : {'view': True, 'header': 'G - Расход среды, кг/с', 'dimension': 'кг/с', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=O24', 'cell': 'O257'}, 'accuracy': 4},
    'd_vnutrennij_diametr_shg_m'
    : {'view': True, 'header': 'D - Внутренний диаметр ШГ, м', 'dimension': 'м', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=E27', 'cell': 'O258'}, 'accuracy': 4},
    'pat_atmosfernoe_davlenie_pa'
    : {'view': True, 'header': 'paт - Атмосферное давление, Па', 'dimension': 'Па', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=E63', 'cell': 'O259'}, 'accuracy': 4},
    'ss_summarnaya_ploschad_vseh_kanalov_m2'
    : {'view': True, 'header': 'Ss - Суммарная площадь всех каналов, м2', 'dimension': 'м2', 'comment': 'ф. (5.195)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=SUM(O315,O330,O345,O360,O375,O390)', 'cell': 'O260'}, 'accuracy': 4},
    'summ_diam'
    : {'view': True, 'header': 'Σ', 'dimension': '', 'comment': 'ф. (5.198)',
       'formula': {
           'expr': '=ЕСЛИ(И(O388="";O343="";O373="";O358="";O328="");O315*КОРЕНЬ(O313);ЕСЛИ(И(O388="";O373="";O358="";O343="");СУММ(O315*КОРЕНЬ(O313);O330*КОРЕНЬ(O328));ЕСЛИ(И(O388="";O373="";O358="");СУММ(O315*КОРЕНЬ(O313);O330*КОРЕНЬ(O328);O345*КОРЕНЬ(O343));ЕСЛИ(И(O388="";O373="");СУММ(O315*КОРЕНЬ(O313);O330*КОРЕНЬ(O328);O345*КОРЕНЬ(O343);O360*КОРЕНЬ(O358));ЕСЛИ(O388="";СУММ(O315*КОРЕНЬ(O313);O330*КОРЕНЬ(O328);O345*КОРЕНЬ(O343);O360*КОРЕНЬ(O358);O375*КОРЕНЬ(O373));СУММ(O315*КОРЕНЬ(O313);O330*КОРЕНЬ(O328);O345*КОРЕНЬ(O343);O360*КОРЕНЬ(O358);O375*КОРЕНЬ(O373);O390*КОРЕНЬ(O388)))))))',
           'cell': 'O261'}, 'accuracy': 4, 'group_name': 'Расчет аэродинамики для кольцевых каналов'},
    'f_otnositelnaya_ploschad'
    : {'view': True, 'header': 'f - Относительная площадь', 'dimension': 'м2', 'comment': 'ф. (5.196)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=4*O260/(PI()*O258^2)', 'cell': 'O262'}, 'accuracy': 4},
    'l_dlina_kanalov_m'
    : {'view': True, 'header': 'l - Длина каналов, м', 'dimension': 'м', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=E29', 'cell': 'O263'}, 'accuracy': 4},
    'pa_pa'
    : {'view': True, 'header': 'pa, Па', 'dimension': 'Па', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=O286', 'cell': 'O265'}, 'accuracy': 4},
    'ptr_pa'
    : {'view': True, 'header': 'Pтр, Па', 'dimension': 'Па', 'comment': 'ф. (5.174)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {
           'expr': '=IF(AND(O388="",O373="",O358="",O343="",O328=""),SQRT($O$257^2*$O$254*$O$256*$E$62*$O$263/(O316)^2+$O$265^2),IF(AND(O388="",O373="",O358="",O343=""),SQRT(O257^2*O254*O256*E62*O263/(SUM(O316,O331))^2+O265^2),IF(AND(O388="",O373="",O358=""),SQRT(O257^2*O254*O256*E62*O263/(SUM(O316,O331,O346))^2+O265^2),IF(AND(O388="",O373=""),SQRT(O257^2*O254*O256*E62*O263/(SUM(O316,O331,O346,O361))^2+O265^2),IF(O388="",SQRT(O257^2*O254*O256*E62*O263/(SUM(O316,O331,O346,O361,O376))^2+O265^2),SQRT(O257^2*O254*O256*E62*O263/(SUM(O316,O331,O346,O361,O376,O391))^2+O265^2))))))',
           'cell': 'O266'}, 'accuracy': 4},
    'pi3_davlenie_pered_stupenyu_zvukopogloscheniya_pa_2'
    : {'view': True, 'header': 'Pi3 - Давление перед ступенью звукопоглощения, Па', 'dimension': 'Па',
       'comment': 'ф. (5.175):',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O253="Есть",O266,IF(O253="Нет",O266+0.5*(1-O262)*O270*O269^2/2))', 'cell': 'O267'},
       'accuracy': 4},
    'maksimalnaya_skorost_mezhdu_kasset_m_s'
    : {'view': True, 'header': 'Максимальная скорость между кассет, м/с', 'dimension': 'м/с', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=MAX(O320,O335,O350,O365,O380,O395)', 'cell': 'O268'}, 'accuracy': 4},
    'v_aero'
    : {'view': True, 'header': 'V', 'dimension': '', 'comment': 'ф. (5.176)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=O257*O254*O256/(O266*O260)', 'cell': 'O269'}, 'accuracy': 4},
    'g_rashod_sredy_kg_s_2'
    : {'view': True, 'header': 'G - Расход среды, кг/с', 'dimension': 'кг/с', 'comment': 'Расчет выхлопной части',
       'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=O24', 'cell': 'O274'}, 'accuracy': 4},
    'k_koefficient_adiabaty'
    : {'view': True, 'header': 'k - Коэффициент адиабаты', 'dimension': '', 'comment': '',
       'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=$O$31', 'cell': 'O275'}, 'accuracy': 4},
    'r_individualnaya_gazovaya_postoyannaya_m2s2_k'
    : {'view': True, 'header': 'R - Индивидуальная газовая постоянная, м2с2/К', 'dimension': '', 'comment': '',
       'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=O29', 'cell': 'O276'}, 'accuracy': 4},
    't_temperatura_sredy_k'
    : {'view': True, 'header': 'Т - Температура среды, К', 'dimension': '°С', 'comment': '',
       'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=O135', 'cell': 'O277'}, 'accuracy': 4},
    'pat_atmosfernoe_davlenie_pa_2'
    : {'view': True, 'header': 'paт - Атмосферное давление, Па', 'dimension': 'Па', 'comment': '',
       'group_name': 'Расчет выхлопной части',
       'formula': {'expr': 101325, 'cell': 'O278'}, 'accuracy': 4},
    'd_vnutrennij_diametr_korpusa_stupeni_zvukopogloscheniya_m'
    : {'view': True, 'header': 'D - Внутренний диаметр корпуса ступени звукопоглощения, м', 'dimension': 'м',
       'comment': '',
       'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=E27', 'cell': 'O279'}, 'accuracy': 4},
    'da_vnutrennij_diametr_vyhlopa_m'
    : {'view': True, 'header': 'Da - Внутренний диаметр выхлопа, м', 'dimension': 'м', 'comment': '',
       'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=O279-2*E28', 'cell': 'O280'}, 'accuracy': 4},
    'hk_osevoe_rasstoyanie_ot_vyhodnogo_secheniya_korpusa_do_kryshki_m'
    : {'view': True, 'header': 'hk - Осевое расстояние от выходного сечения корпуса  до крышки, м', 'dimension': 'м',
       'comment': '',
       'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=E35', 'cell': 'O281'}, 'accuracy': 4},
    'sk_ploschad_vyhodnogo_secheniya_kanala_korpusa_do_kryshki_m2'
    : {'view': True, 'header': 'Sk - Площадь выходного сечения канала корпуса до крышки, м2', 'dimension': 'м2',
       'comment': '',
       'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=PI()*O279*O281', 'cell': 'O282'}, 'accuracy': 4},
    'sa'
    : {'view': True, 'header': 'Sa', 'dimension': '', 'comment': '', 'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=PI()*O280^2/4', 'cell': 'O283'}, 'accuracy': 4},
    'pk_izbytochnoe_davlenie_pod_kryshkoj_pa_2'
    : {'view': True, 'header': 'Pk - Избыточное давление под крышкой, Па', 'dimension': 'Па', 'comment': 'ф. (5.211)',
       'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=O274^2*O276*O277/(2*O278*O282^2)', 'cell': 'O284'}, 'accuracy': 4},
    'pa_izbytochnoe_davlenie_na_vyhode_iz_korpusa_za_stupenyu_zvukopogloscheniya_pa_2'
    : {'view': True, 'header': 'Pa - Избыточное давление на выходе из корпуса за ступенью звукопоглощения, Па',
       'dimension': 'Па',
       'comment': 'ф. (5.212)', 'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=O284+((O274^2*O276*O277)/(2*(O278+O284)*O283^2))*(1-(O280/O279)^4)', 'cell': 'O285'},
       'accuracy': 4},
    'pa_absolyutnoe_davlenie_za_stupenyu_zvukopogloscheniya_pa_2'
    : {'view': True, 'header': 'pa - Абсолютное давление за ступенью звукопоглощения, Па', 'dimension': 'Па',
       'comment': 'ф. (5.213)',
       'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=O285+O278', 'cell': 'O286'}, 'accuracy': 4},
    'pk'
    : {'view': True, 'header': 'pk', 'dimension': '', 'comment': '', 'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=O284+O278', 'cell': 'O290'}, 'accuracy': 4},
    'wa_skorost_na_vyhode_iz_korpusa_m_s_2'
    : {'view': True, 'header': 'wa - Скорость на выходе из корпуса, м/с', 'dimension': 'м/с', 'comment': 'ф. (5.214)',
       'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=(O274*O276*O277)/(O290*O283)', 'cell': 'O291'}, 'accuracy': 4},
    'wk_skorost_na_vyhlope_v_atmosferu_m_s_2'
    : {'view': True, 'header': 'wk - Скорость на выхлопе в атмосферу, м/с', 'dimension': 'м/с', 'comment': 'ф. (5.215)',
       'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=(O274*O276*O277)/(O278*O282)', 'cell': 'O292'}, 'accuracy': 4},
    'ma_chislo_maha_na_vyhode_iz_korpusa_2'
    : {'view': True, 'header': 'Ma - Число Маха на выходе из корпуса', 'dimension': '', 'comment': 'ф. (5.216)',
       'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=O291/SQRT(O275*O276*O277)', 'cell': 'O293'}, 'accuracy': 4},
    'mk_chislo_maha_na_vyhlope_v_atmosferu_2'
    : {'view': True, 'header': 'Mk - Число Маха на выхлопе в атмосферу', 'dimension': '', 'comment': 'ф. (5.217)',
       'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=O292/SQRT(O275*O276*O277)', 'cell': 'O294'}, 'accuracy': 4},
    'k_ma'
    : {'view': True, 'header': 'k(Ma)', 'dimension': '', 'comment': 'ф. (1.15)', 'group_name': 'Расчет выхлопной части',
       'formula': {
           'expr': '=IF(O293<=SQRT(0.8),8*10^(-5)*O293^3,IF(AND(O293>SQRT(0.8),O293<=20^0.2),10^(-4)*O293^5,IF(O293>20^0.2,2*10^(-3))))',
           'cell': 'O295'}, 'accuracy': 4},
    'k_mk'
    : {'view': True, 'header': 'K(Mk)', 'dimension': '', 'comment': '', 'group_name': 'Расчет выхлопной части',
       'formula': {
           'expr': '=IF(O294<=SQRT(0.8),8*10^(-5)*O294^3,IF(AND(O294>SQRT(0.8),O294<=20^0.2),10^(-4)*O294^5,IF(O294>20^0.2,2*10^(-3))))',
           'cell': 'O296'}, 'accuracy': 4},
    'wa_moschnost_shuma_na_vyhode_iz_korpusa_vt'
    : {'view': True, 'header': 'Wa - Мощность шума на выходе из корпуса, Вт', 'dimension': 'Вт',
       'comment': 'ф. (5.218)',
       'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=O295*O274*O291^2/2', 'cell': 'O297'}, 'accuracy': 4},
    'wk_moschnost_shuma_na_vyhode_iz_pod_kryshki_vt'
    : {'view': True, 'header': 'Wk - Мощность шума на выходе из-под крышки, Вт', 'dimension': 'Вт', 'comment': '',
       'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=O296*O274*O292^2/2', 'cell': 'O298'}, 'accuracy': 4},
    'lwa_uzm_generiruemyj_istecheniem_iz_korpusa_db'
    : {'view': True, 'header': 'Lwa -УЗМ, генерируемый истечением из корпуса, дБ', 'dimension': 'дБ',
       'comment': 'ф. (5.57)',
       'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=10*LOG10(O297/(10^(-12)))', 'cell': 'O299'}, 'accuracy': 4},
    'lwk_uzm_generiruemyj_istecheniem_iz_pod_kryshki_db'
    : {'view': True, 'header': 'Lwk -УЗМ, генерируемый истечением из-под крышки, дБ', 'dimension': 'дБ', 'comment': '',
       'group_name': 'Расчет выхлопной части',
       'formula': {'expr': '=10*LOG10(O298/(10^(-12)))', 'cell': 'O300'}, 'accuracy': 4},
    'dinamicheskaya_nagruzka_na_drosselnyj_blok_kn_2'
    : {'view': True, 'header': 'Динамическая нагрузка на дроссельный блок, кН', 'dimension': '', 'comment': '',
       'group_name': 'Динамические нагрузки',
       'formula': {'expr': '=(($O$31+1)/(2*$O$31)*O24*O28*(O16+1/O16)-O153*(PI()*E36^2/4))*0.001', 'cell': 'O304'},
       'accuracy': 4},
    'dinamicheskaya_nagruzka_na_stupen_zvukopogloscheniya_kn_2'
    : {'view': True, 'header': 'Динамическая нагрузка на ступень звукопоглощения, кН', 'dimension': '', 'comment': '',
       'group_name': 'Динамические нагрузки',
       'formula': {'expr': '=(PI()*O258^2/4)*(O267-O265)*0.001', 'cell': 'O305'}, 'accuracy': 4},
    'dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_bokovom_vyhlope_kn_2'
    : {'view': True, 'header': 'Динамическая нагрузка на защитную крышку при боковом выхлопе, кН', 'dimension': '',
       'comment': '',
       'group_name': 'Динамические нагрузки',
       'formula': {'expr': '=(PI()*POWER(O279,2)/4)*O284*0.001', 'cell': 'O306'}, 'accuracy': 4},
    'dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_osevom_vyhlope_kn_2'
    : {'view': True, 'header': 'Динамическая нагрузка на защитную крышку при осевом выхлопе, кН', 'dimension': '',
       'comment': '',
       'group_name': 'Динамические нагрузки',
       'formula': {'expr': '=IF((PI()*POWER(O279,2)/4-O282)<0,0,(PI()*POWER(O279,2)/4-O282)*O284*0.001)',
                   'cell': 'O307'}, 'accuracy': 4},
    'davlenie_na_dnische_drosselnogo_bloka_mpa'
    : {'view': True, 'header': 'Давление на днище дроссельного блока, МПа', 'dimension': 'МПа', 'comment': '',
       'group_name': 'Динамические нагрузки',
       'formula': {'expr': '=O170*10^3/(PI()*(E36-2*(E37*10^-3))^2/4)*10^-6', 'cell': 'O308'}, 'accuracy': 4},
    'r_vnutrennij_radius_m_n1'
    : {'view': True, 'header': 'r - Внутренний радиус, м N1', 'dimension': 'м', 'comment': 'Динамические нагрузки',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(AND(E42=0,E41>=1),E43*0.001,0)', 'cell': 'O311'}, 'accuracy': 4},
    'r_naruzhnyj_radius_m_n1'
    : {'view': True, 'header': 'R - Наружный радиус, м N1', 'dimension': 'м', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(AND(E42=0,E41>=1),O311+E44*0.001,IF(E42>0,E42*0.001))', 'cell': 'O312'}, 'accuracy': 4},
    'dh_gidravlicheskij_diametr_m_n1'
    : {'view': True, 'header': 'Dh - Гидравлический диаметр, м N1', 'dimension': 'м', 'comment': 'ф. (5.194)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=2*(O312-O311)', 'cell': 'O313'}, 'accuracy': 4},
    'd_shirina_kanala_m_n1'
    : {'view': True, 'header': 'd - Ширина канала, м N1', 'dimension': 'м', 'comment': 'ф. (5.199)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=O312-O311', 'cell': 'O314'}, 'accuracy': 4},
    'f_ploschad_kanala_m2_n1'
    : {'view': True, 'header': 'F - Площадь канала, м2 N1', 'dimension': 'м2', 'comment': 'ф. (5.193)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=PI()*(O312^2-O311^2)', 'cell': 'O315'}, 'accuracy': 4},
    'f_dh_0_5_n1'
    : {'view': True, 'header': 'F*(Dh)^0,5 N1', 'dimension': '', 'comment': 'Промежуточный расчет для ф. (5.192)\n',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=O315*SQRT(O313)', 'cell': 'O316'}, 'accuracy': 4},
    'h_srednyaya_tolschina_plastin_m_n1'
    : {'view': True, 'header': 'h - Средняя толщина пластин, м N1', 'dimension': 'м',
       'comment': 'ф. (5.200):\n Средняя толщина ограничивающих канал пластин',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(E42=0,(O311*E43*2*0.001+O312*E45*0.001)/(O311+O312),(O312*E43*0.001)/O312)',
                   'cell': 'O317'}, 'accuracy': 4},
    'pd_skorostnoj_napor_na_vyhode_pa_n1'
    : {'view': True, 'header': 'Pd - Скоростной напор на выходе, Па N1', 'dimension': 'Па',
       'comment': 'ф. (5.197):\nСкоростной напор на выходе кольцевого канала',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=O257^2*O313*O254*O256/(2*O259*O261^2)', 'cell': 'O318'}, 'accuracy': 4},
    'g_rashod_v_kanale_kg_s_n1'
    : {'view': True, 'header': 'G - Расход в канале, кг/с N1', 'dimension': 'кг/с', 'comment': 'ф. (5.205)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=(O257*O315*SQRT(O313))/O261', 'cell': 'O319'}, 'accuracy': 4},
    'w_skorost_v_kanale_m_s_n1'
    : {'view': True, 'header': 'w - Скорость в канале, м/с N1', 'dimension': 'м/с', 'comment': 'ф. (5.206)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=(O319*O254*O256)/(O259*O315)', 'cell': 'O320'}, 'accuracy': 4},
    'm_chislo_maha_v_kanale_n1'
    : {'view': True, 'header': 'М - Число Маха в канале N1', 'dimension': '', 'comment': 'ф. (5.207)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=O320/SQRT(O255*O254*O256)', 'cell': 'O321'}, 'accuracy': 4},
    'k_m_n1'
    : {'view': True, 'header': 'k(M) N1', 'dimension': '', 'comment': 'ф. (1.15)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {
           'expr': '=IF(O321<=SQRT(0.8),8*10^(-5)*O321^3,IF(AND(O321>SQRT(0.8),O321<=20^0.2),10^(-4)*O321^5,IF(O321>20^0.2,2*10^(-3))))',
           'cell': 'O322'}, 'accuracy': 4},
    'ds_n1'
    : {'view': True, 'header': 'ds N1', 'dimension': '', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=MIN(O314,O317)', 'cell': 'O323'}, 'accuracy': 4},
    'ws_moschnost_shuma_na_vyhode_kanala_vt_n1'
    : {'view': True, 'header': 'Ws - Мощность шума на выходе канала, Вт N1', 'dimension': 'Вт', 'comment': 'ф. (5.204)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=O322*O319*(O320^2)/2*SQRT((O312+O311)/(O312-O311))', 'cell': 'O324'}, 'accuracy': 4},
    'lws_n1'
    : {'view': True, 'header': 'Lws  N1', 'dimension': '',
       'comment': 'ф. (5.57):\nУровень звуковой мощности, генерируемой потоком в кольцевом канале 1\n',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=10*LOG10(O324/(10^(-12)))', 'cell': 'O325'}, 'accuracy': 4},
    'r_vnutrennij_radius_m_n2'
    : {'view': True, 'header': 'r - Внутренний радиус, м N2', 'dimension': 'м', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {
           'expr': '=IF(AND(E42=0,E41=1),"",IF(AND(E42=0,E41>=2),O312+E45*0.001,IF(AND(E42>0,E41>=1),O312+E43*0.001)))',
           'cell': 'O326'}, 'accuracy': 4},
    'r_naruzhnyj_radius_m_n2'
    : {'view': True, 'header': 'R - Наружный радиус, м N2', 'dimension': 'м', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {
           'expr': '=IF(AND(E42=0,E41=1),"",IF(AND(E42=0,E41>=2),O326+E46*0.001,IF(AND(E42>0,E41>=1),O326+E44*0.001)))',
           'cell': 'O327'}, 'accuracy': 4},
    'dh_gidravlicheskij_diametr_m_n2'
    : {'view': True, 'header': 'Dh - Гидравлический диаметр, м N2', 'dimension': 'м', 'comment': 'ф. (5.194)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(AND(O326="",O327=""),"",2*(O327-O326))', 'cell': 'O328'}, 'accuracy': 4},
    'd_shirina_kanala_m_n2'
    : {'view': True, 'header': 'd - Ширина канала, м N2', 'dimension': 'м', 'comment': 'ф. (5.199)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(AND(O327="",O326=""),"",O327-O326)', 'cell': 'O329'}, 'accuracy': 4},
    'f_ploschad_kanala_m2_n2'
    : {'view': True, 'header': 'F - Площадь канала, м2 N2', 'dimension': 'м2', 'comment': 'ф. (5.193)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(AND(O326="",O327=""),"",PI()*(O327^2-O326^2))', 'cell': 'O330'}, 'accuracy': 4},
    'f_dh_0_5_n2'
    : {'view': True, 'header': 'F*(Dh)^0,5 N2', 'dimension': '', 'comment': 'Промежуточный расчет для ф. (5.192)\n',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O328="","",O330*SQRT(O328))', 'cell': 'O331'}, 'accuracy': 4},
    'h_srednyaya_tolschina_plastin_m_n2'
    : {'view': True, 'header': 'h - Средняя толщина пластин, м N2', 'dimension': 'м',
       'comment': 'ф. (5.200):\n Средняя толщина ограничивающих канал пластин',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {
           'expr': '=IF(O326="","",IF(E42=0,(O326*E45*0.001+O327*E47*0.001)/(O326+O327),(O326*E43*0.001+O327*E45*0.001)/(O326+O327)))',
           'cell': 'O332'}, 'accuracy': 4},
    'pd_skorostnoj_napor_na_vyhode_pa_n2'
    : {'view': True, 'header': 'Pd - Скоростной напор на выходе, Па N2', 'dimension': 'Па',
       'comment': 'ф. (5.197):\nСкоростной напор на выходе кольцевого канала',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O328="","",O257^2*O328*O254*O256/(2*O259*O261^2))', 'cell': 'O333'}, 'accuracy': 4},
    'g_rashod_v_kanale_kg_s_n2'
    : {'view': True, 'header': 'G - Расход в канале, кг/с N2', 'dimension': 'кг/с', 'comment': 'ф. (5.205)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O328="","",(O257*O330*SQRT(O328))/O261)', 'cell': 'O334'}, 'accuracy': 4},
    'w_skorost_v_kanale_m_s_n2'
    : {'view': True, 'header': 'w - Скорость в канале, м/с N2', 'dimension': 'м/с', 'comment': 'ф. (5.206)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O328="","",(O334*O254*O256)/(O259*O330))', 'cell': 'O335'}, 'accuracy': 4},
    'm_chislo_maha_v_kanale_n2'
    : {'view': True, 'header': 'М - Число Маха в канале N2', 'dimension': '', 'comment': 'ф. (5.207)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O328="","",O335/SQRT(O255*O254*O256))', 'cell': 'O336'}, 'accuracy': 4},
    'k_m_n2'
    : {'view': True, 'header': 'k(M) N2', 'dimension': '', 'comment': 'ф. (1.15)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {
           'expr': '=IF(O336="","",IF(O336<=SQRT(0.8),8*10^(-5)*O336^3,IF(AND(O336>SQRT(0.8),O336<=20^0.2),10^(-4)*O336^5,IF(O336>20^0.2,2*10^(-3)))))',
           'cell': 'O337'}, 'accuracy': 4},
    'ds_n2'
    : {'view': True, 'header': 'ds N2', 'dimension': '', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O329="","",MIN(O329,O332))', 'cell': 'O338'}, 'accuracy': 4},
    'ws_moschnost_shuma_na_vyhode_kanala_vt_n2'
    : {'view': True, 'header': 'Ws - Мощность шума на выходе канала, Вт N2', 'dimension': 'Вт', 'comment': 'ф. (5.204)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O334="","",O337*O334*(O335^2)/2*SQRT((O327+O326)/(O327-O326)))', 'cell': 'O339'},
       'accuracy': 4},
    'lws_n2'
    : {'view': True, 'header': 'Lws  N2', 'dimension': '',
       'comment': 'ф. (5.57):\nУровень звуковой мощности, генерируемой потоком в кольцевом канале 1\n',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O339="","",10*LOG10(O339/(10^(-12))))', 'cell': 'O340'}, 'accuracy': 4},
    'r_vnutrennij_radius_m_n3'
    : {'view': True, 'header': 'r - Внутренний радиус, м N3', 'dimension': 'м', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {
           'expr': '=IF(AND(E42=0,E41<=2),"",IF(AND(E42=0,E41>=3),O327+E47*0.001,IF(AND(E42>0,E41<=1),"",IF(AND(E42>0,E41>=2),O327+E45*0.001))))',
           'cell': 'O341'}, 'accuracy': 4},
    'r_naruzhnyj_radius_m_n3'
    : {'view': True, 'header': 'R - Наружный радиус, м N3', 'dimension': 'м', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {
           'expr': '=IF(AND(E42=0,E41<=2),"",IF(AND(E42=0,E41>=3),O341+E48*0.001,IF(AND(E42>0,E41<=1),"",IF(AND(E42>0,E41>=2),O341+E46*0.001))))',
           'cell': 'O342'}, 'accuracy': 4},
    'dh_gidravlicheskij_diametr_m_n3'
    : {'view': True, 'header': 'Dh - Гидравлический диаметр, м N3', 'dimension': 'м', 'comment': 'ф. (5.194)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(AND(O341="",O342=""),"",2*(O342-O341))', 'cell': 'O343'}, 'accuracy': 4},
    'd_shirina_kanala_m_n3'
    : {'view': True, 'header': 'd - Ширина канала, м N3', 'dimension': 'м', 'comment': 'ф. (5.199)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(AND(O341="",O342=""),"",O342-O341)', 'cell': 'O344'}, 'accuracy': 4},
    'f_ploschad_kanala_m2_n3'
    : {'view': True, 'header': 'F - Площадь канала, м2 N3', 'dimension': 'м2', 'comment': 'ф. (5.193)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(AND(O341="",O342=""),"",PI()*(O342^2-O341^2))', 'cell': 'O345'}, 'accuracy': 4},
    'f_dh_0_5_n3'
    : {'view': True, 'header': 'F*(Dh)^0,5 N3', 'dimension': '', 'comment': 'Промежуточный расчет для ф. (5.192)\n',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O343="","",O345*SQRT(O343))', 'cell': 'O346'}, 'accuracy': 4},
    'h_srednyaya_tolschina_plastin_m_n3'
    : {'view': True, 'header': 'h - Средняя толщина пластин, м N3', 'dimension': 'м',
       'comment': 'ф. (5.200):\n Средняя толщина ограничивающих канал пластин',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {
           'expr': '=IF(O344="","",IF(E42=0,(O341*E47*0.001+O342*E49*0.001)/(O341+O342),(O341*E45*0.001+O342*E47*0.001)/(O341+O342)))',
           'cell': 'O347'}, 'accuracy': 4},
    'pd_skorostnoj_napor_na_vyhode_pa_n3'
    : {'view': True, 'header': 'Pd - Скоростной напор на выходе, Па N3', 'dimension': 'Па',
       'comment': 'ф. (5.197):\nСкоростной напор на выходе кольцевого канала',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O343="","",O257^2*O343*O254*O256/(2*O259*O261^2))', 'cell': 'O348'}, 'accuracy': 4},
    'g_rashod_v_kanale_kg_s_n3'
    : {'view': True, 'header': 'G - Расход в канале, кг/с N3', 'dimension': 'кг/с', 'comment': 'ф. (5.205)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O343="","",(O257*O345*SQRT(O343))/O261)', 'cell': 'O349'}, 'accuracy': 4},
    'w_skorost_v_kanale_m_s_n3'
    : {'view': True, 'header': 'w - Скорость в канале, м/с N3', 'dimension': 'м/с', 'comment': 'ф. (5.206)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O343="","",(O349*O254*O256)/(O259*O345))', 'cell': 'O350'}, 'accuracy': 4},
    'm_chislo_maha_v_kanale_n3'
    : {'view': True, 'header': 'М - Число Маха в канале N3', 'dimension': '', 'comment': 'ф. (5.207)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O343="","",O350/SQRT(O255*O254*O256))', 'cell': 'O351'}, 'accuracy': 4},
    'k_m_n3'
    : {'view': True, 'header': 'k(M) N3', 'dimension': '', 'comment': 'ф. (1.15)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {
           'expr': '=IF(O351="","",IF(O351<=SQRT(0.8),8*10^(-5)*O351^3,IF(AND(O351>SQRT(0.8),O351<=20^0.2),10^(-4)*O351^5,IF(O351>20^0.2,2*10^(-3)))))',
           'cell': 'O352'}, 'accuracy': 4},
    'ds_n3'
    : {'view': True, 'header': 'ds N3', 'dimension': '', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O344="","",MIN(O344,O347))', 'cell': 'O353'}, 'accuracy': 4},
    'ws_moschnost_shuma_na_vyhode_kanala_vt_n3'
    : {'view': True, 'header': 'Ws - Мощность шума на выходе канала, Вт N3', 'dimension': 'Вт', 'comment': 'ф. (5.204)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O349="","",O352*O349*(O350^2)/2*SQRT((O342+O341)/(O342-O341)))', 'cell': 'O354'},
       'accuracy': 4},
    'lws_n3'
    : {'view': True, 'header': 'Lws  N3', 'dimension': '',
       'comment': 'ф. (5.57):\nУровень звуковой мощности, генерируемой потоком в кольцевом канале 1\n',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O354="","",10*LOG10(O354/(10^(-12))))', 'cell': 'O355'}, 'accuracy': 4},
    'r_vnutrennij_radius_m_n4'
    : {'view': True, 'header': 'r - Внутренний радиус, м N4', 'dimension': 'м', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {
           'expr': '=IF(AND(E42=0,E41<=3),"",IF(AND(E42=0,E41>=4),O342+E49*0.001,IF(AND(E42>0,E41<=2),"",IF(AND(E42>0,E41>=2),O342+E47*0.001))))',
           'cell': 'O356'}, 'accuracy': 4},
    'r_naruzhnyj_radius_m_n4'
    : {'view': True, 'header': 'R - Наружный радиус, м N4', 'dimension': 'м', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {
           'expr': '=IF(AND(E42=0,E41<=3),"",IF(AND(E42=0,E41>=4),O356+E50*0.001,IF(AND(E42>0,E41<=2),"",IF(AND(E42>0,E41>=3),O356+E48*0.001))))',
           'cell': 'O357'}, 'accuracy': 4},
    'dh_gidravlicheskij_diametr_m_n4'
    : {'view': True, 'header': 'Dh - Гидравлический диаметр, м N4', 'dimension': 'м', 'comment': 'ф. (5.194)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(AND(O356="",O357=""),"",2*(O357-O356))', 'cell': 'O358'}, 'accuracy': 4},
    'd_shirina_kanala_m_n4'
    : {'view': True, 'header': 'd - Ширина канала, м N4', 'dimension': 'м', 'comment': 'ф. (5.199)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(AND(O356="",O357=""),"",O357-O356)', 'cell': 'O359'}, 'accuracy': 4},
    'f_ploschad_kanala_m2_n4'
    : {'view': True, 'header': 'F - Площадь канала, м2 N4', 'dimension': 'м2', 'comment': 'ф. (5.193)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(AND(O356="",O357=""),"",PI()*(O357^2-O356^2))', 'cell': 'O360'}, 'accuracy': 4},
    'f_dh_0_5_n4'
    : {'view': True, 'header': 'F*(Dh)^0,5 N4', 'dimension': '', 'comment': 'Промежуточный расчет для ф. (5.192)\n',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O358="","",O360*SQRT(O358))', 'cell': 'O361'}, 'accuracy': 4},
    'h_srednyaya_tolschina_plastin_m_n4'
    : {'view': True, 'header': 'h - Средняя толщина пластин, м N4', 'dimension': 'м',
       'comment': 'ф. (5.200):\n Средняя толщина ограничивающих канал пластин',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {
           'expr': '=IF(O359="","",IF(E42=0,(O356*E49*0.001+O357*E51*0.001)/(O356+O357),(O356*E47*0.001+O357*E49*0.001)/(O356+O357)))',
           'cell': 'O362'}, 'accuracy': 4},
    'pd_skorostnoj_napor_na_vyhode_pa_n4'
    : {'view': True, 'header': 'Pd - Скоростной напор на выходе, Па N4', 'dimension': 'Па',
       'comment': 'ф. (5.197):\nСкоростной напор на выходе кольцевого канала',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O358="","",$O$257^2*O358*$O$254*$O$256/(2*$O$259*$O$261^2))', 'cell': 'O363'},
       'accuracy': 4},
    'g_rashod_v_kanale_kg_s_n4'
    : {'view': True, 'header': 'G - Расход в канале, кг/с N4', 'dimension': 'кг/с', 'comment': 'ф. (5.205)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O358="","",(O257*O360*SQRT(O358))/O261)', 'cell': 'O364'}, 'accuracy': 4},
    'w_skorost_v_kanale_m_s_n4'
    : {'view': True, 'header': 'w - Скорость в канале, м/с N4', 'dimension': 'м/с', 'comment': 'ф. (5.206)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O358="","",(O364*$O$254*$O$256)/($O$259*O360))', 'cell': 'O365'}, 'accuracy': 4},
    'm_chislo_maha_v_kanale_n4'
    : {'view': True, 'header': 'М - Число Маха в канале N4', 'dimension': '', 'comment': 'ф. (5.207)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O358="","",O365/SQRT($O$255*$O$254*$O$256))', 'cell': 'O366'}, 'accuracy': 4},
    'k_m_n4'
    : {'view': True, 'header': 'k(M) N4', 'dimension': '', 'comment': 'ф. (1.15)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {
           'expr': '=IF(O366="","",IF(O366<=SQRT(0.8),8*10^(-5)*O366^3,IF(AND(O366>SQRT(0.8),O366<=20^0.2),10^(-4)*O366^5,IF(O366>20^0.2,2*10^(-3)))))',
           'cell': 'O367'}, 'accuracy': 4},
    'ds_n4'
    : {'view': True, 'header': 'ds N4', 'dimension': '', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O359="","",MIN(O359,O362))', 'cell': 'O368'}, 'accuracy': 4},
    'ws_moschnost_shuma_na_vyhode_kanala_vt_n4'
    : {'view': True, 'header': 'Ws - Мощность шума на выходе канала, Вт N4', 'dimension': 'Вт', 'comment': 'ф. (5.204)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O364="","",O367*O364*(O365^2)/2*SQRT((O357+O356)/(O357-O356)))', 'cell': 'O369'},
       'accuracy': 4},
    'lws_n4'
    : {'view': True, 'header': 'Lws  N4', 'dimension': '',
       'comment': 'ф. (5.57):\nУровень звуковой мощности, генерируемой потоком в кольцевом канале 1\n',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O369="","",10*LOG10(O369/(10^(-12))))', 'cell': 'O370'}, 'accuracy': 4},
    'r_vnutrennij_radius_m_n5'
    : {'view': True, 'header': 'r - Внутренний радиус, м N5', 'dimension': 'м', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {
           'expr': '=IF(AND(E42=0,E41<=4),"",IF(AND(E42=0,E41>=5),O357+E51*0.001,IF(AND(E42>0,E41<=3),"",IF(AND(E42>0,E41>=4),O357+E49*0.001))))',
           'cell': 'O371'}, 'accuracy': 4},
    'r_naruzhnyj_radius_m_n5'
    : {'view': True, 'header': 'R - Наружный радиус, м N5', 'dimension': 'м', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {
           'expr': '=IF(AND(E42=0,E41<=4),"",IF(AND(E42=0,E41>4),O371+E52*0.001,IF(AND(E42>0,E41<=3),"",IF(AND(E42>0,E41>=4),O371+E50*0.001))))',
           'cell': 'O372'}, 'accuracy': 4},
    'dh_gidravlicheskij_diametr_m_n5'
    : {'view': True, 'header': 'Dh - Гидравлический диаметр, м N5', 'dimension': 'м', 'comment': 'ф. (5.194)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(AND(O371="",O372=""),"",2*(O372-O371))', 'cell': 'O373'}, 'accuracy': 4},
    'd_shirina_kanala_m_n5'
    : {'view': True, 'header': 'd - Ширина канала, м N5', 'dimension': 'м', 'comment': 'ф. (5.199)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(AND(O371="",O372=""),"",O372-O371)', 'cell': 'O374'}, 'accuracy': 4},
    'f_ploschad_kanala_m2_n5'
    : {'view': True, 'header': 'F - Площадь канала, м2 N5', 'dimension': 'м2', 'comment': 'ф. (5.193)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(AND(O371="",O372=""),"",PI()*(O372^2-O371^2))', 'cell': 'O375'}, 'accuracy': 4},
    'f_dh_0_5_n5'
    : {'view': True, 'header': 'F*(Dh)^0,5 N5', 'dimension': '', 'comment': 'Промежуточный расчет для ф. (5.192)\n',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O373="","",O375*SQRT(O373))', 'cell': 'O376'}, 'accuracy': 4},
    'h_srednyaya_tolschina_plastin_m_n5'
    : {'view': True, 'header': 'h - Средняя толщина пластин, м N5', 'dimension': 'м',
       'comment': 'ф. (5.200):\n Средняя толщина ограничивающих канал пластин',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {
           'expr': '=IF(O374="","",IF(E42=0,(O371*E51*0.001+O372*E53*0.001)/(O371+O372),(O371*E49*0.001+O372*E51*0.001)/(O371+O372)))',
           'cell': 'O377'}, 'accuracy': 4},
    'pd_skorostnoj_napor_na_vyhode_pa_n5'
    : {'view': True, 'header': 'Pd - Скоростной напор на выходе, Па N5', 'dimension': 'Па',
       'comment': 'ф. (5.197):\nСкоростной напор на выходе кольцевого канала',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O373="","",$O$257^2*O373*$O$254*$O$256/(2*$O$259*$O$261^2))', 'cell': 'O378'},
       'accuracy': 4},
    'g_rashod_v_kanale_kg_s_n5'
    : {'view': True, 'header': 'G - Расход в канале, кг/с N5', 'dimension': 'кг/с', 'comment': 'ф. (5.205)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O373="","",($O$257*O375*SQRT(O373))/$O$261)', 'cell': 'O379'}, 'accuracy': 4},
    'w_skorost_v_kanale_m_s_n5'
    : {'view': True, 'header': 'w - Скорость в канале, м/с N5', 'dimension': 'м/с', 'comment': 'ф. (5.206)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O373="","",(O379*$O$254*$O$256)/($O$259*O375))', 'cell': 'O380'}, 'accuracy': 4},
    'm_chislo_maha_v_kanale_n5'
    : {'view': True, 'header': 'М - Число Маха в канале N5', 'dimension': '', 'comment': 'ф. (5.207)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O373="","",O380/SQRT($O$255*$O$254*$O$256))', 'cell': 'O381'}, 'accuracy': 4},
    'k_m_n5'
    : {'view': True, 'header': 'k(M) N5', 'dimension': '', 'comment': 'ф. (1.15)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {
           'expr': '=IF(O381="","",IF(O381<=SQRT(0.8),8*10^(-5)*O381^3,IF(AND(O381>SQRT(0.8),O381<=20^0.2),10^(-4)*O381^5,IF(O381>20^0.2,2*10^(-3)))))',
           'cell': 'O382'}, 'accuracy': 4},
    'ds_n5'
    : {'view': True, 'header': 'ds N5', 'dimension': '', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O374="","",MIN(O374,O377))', 'cell': 'O383'}, 'accuracy': 4},
    'ws_moschnost_shuma_na_vyhode_kanala_vt_n5'
    : {'view': True, 'header': 'Ws - Мощность шума на выходе канала, Вт N5', 'dimension': 'Вт', 'comment': 'ф. (5.204)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O379="","",O382*O379*(O380^2)/2*SQRT((O372+O371)/(O372-O371)))', 'cell': 'O384'},
       'accuracy': 4},
    'lws_n5'
    : {'view': True, 'header': 'Lws  N5', 'dimension': '',
       'comment': 'ф. (5.57):\nУровень звуковой мощности, генерируемой потоком в кольцевом канале 1\n',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O384="","",10*LOG10(O384/(10^(-12))))', 'cell': 'O385'}, 'accuracy': 4},
    'r_vnutrennij_radius_m_n6'
    : {'view': True, 'header': 'r - Внутренний радиус, м N6', 'dimension': 'м', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(E42=0,"",IF(AND(E42>0,E41<=4),"",IF(AND(E42>0,E41>=5),O372+E51*0.001)))',
                   'cell': 'O386'}, 'accuracy': 4},
    'r_naruzhnyj_radius_m_n6'
    : {'view': True, 'header': 'R - Наружный радиус, м N6', 'dimension': 'м', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(E42=0,"",IF(AND(E42>0,E41<=4),"",IF(AND(E42>0,E41>=5),O386+E52*0.001)))',
                   'cell': 'O387'}, 'accuracy': 4},
    'dh_gidravlicheskij_diametr_m_n6'
    : {'view': True, 'header': 'Dh - Гидравлический диаметр, м N6', 'dimension': 'м', 'comment': 'ф. (5.194)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(AND(O386="",O387=""),"",2*(O387-O386))', 'cell': 'O388'}, 'accuracy': 4},
    'd_shirina_kanala_m_n6'
    : {'view': True, 'header': 'd - Ширина канала, м N6', 'dimension': 'м', 'comment': 'ф. (5.199)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(AND(O386="",O387=""),"",O387-O386)', 'cell': 'O389'}, 'accuracy': 4},
    'f_ploschad_kanala_m2_n6'
    : {'view': True, 'header': 'F - Площадь канала, м2 N6', 'dimension': 'м2', 'comment': 'ф. (5.193)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(AND(O386="",O387=""),"",PI()*(O387^2-O386^2))', 'cell': 'O390'}, 'accuracy': 4},
    'f_dh_0_5_n6'
    : {'view': True, 'header': 'F*(Dh)^0,5 N6', 'dimension': '', 'comment': 'Промежуточный расчет для ф. (5.192)\n',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O388="","",O390*SQRT(O388))', 'cell': 'O391'}, 'accuracy': 4},
    'h_srednyaya_tolschina_plastin_m_n6'
    : {'view': True, 'header': 'h - Средняя толщина пластин, м N6', 'dimension': 'м',
       'comment': 'ф. (5.200):\n Средняя толщина ограничивающих канал пластин',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O389="","",IF(E42>0,(O386*E51*0.001+O387*E53*0.001)/(O386+O387)))', 'cell': 'O392'},
       'accuracy': 4},
    'pd_skorostnoj_napor_na_vyhode_pa_n6'
    : {'view': True, 'header': 'Pd - Скоростной напор на выходе, Па N6', 'dimension': 'Па',
       'comment': 'ф. (5.197):\nСкоростной напор на выходе кольцевого канала',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O388="","",$O$257^2*O388*$O$254*$O$256/(2*$O$259*$O$261^2))', 'cell': 'O393'},
       'accuracy': 4},
    'g_rashod_v_kanale_kg_s_n6'
    : {'view': True, 'header': 'G - Расход в канале, кг/с N6', 'dimension': 'кг/с', 'comment': 'ф. (5.205)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O388="","",($O$257*O390*SQRT(O388))/$O$261)', 'cell': 'O394'}, 'accuracy': 4},
    'w_skorost_v_kanale_m_s_n6'
    : {'view': True, 'header': 'w - Скорость в канале, м/с N6', 'dimension': 'м/с', 'comment': 'ф. (5.206)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O388="","",(O394*$O$254*$O$256)/($O$259*O390))', 'cell': 'O395'}, 'accuracy': 4},
    'm_chislo_maha_v_kanale_n6'
    : {'view': True, 'header': 'М - Число Маха в канале N6', 'dimension': '', 'comment': 'ф. (5.207)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O388="","",O395/SQRT($O$255*$O$254*$O$256))', 'cell': 'O396'}, 'accuracy': 4},
    'k_m_n6'
    : {'view': True, 'header': 'k(M) N6', 'dimension': '', 'comment': 'ф. (1.15)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {
           'expr': '=IF(O396="","",IF(O396<=SQRT(0.8),8*10^(-5)*O396^3,IF(AND(O396>SQRT(0.8),O396<=20^0.2),10^(-4)*O396^5,IF(O396>20^0.2,2*10^(-3)))))',
           'cell': 'O397'}, 'accuracy': 4},
    'ds_n6'
    : {'view': True, 'header': 'ds N6', 'dimension': '', 'comment': '',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O389="","",MIN(O389,O392))', 'cell': 'O398'}, 'accuracy': 4},
    'ws_moschnost_shuma_na_vyhode_kanala_vt_n6'
    : {'view': True, 'header': 'Ws - Мощность шума на выходе канала, Вт N6', 'dimension': 'Вт', 'comment': 'ф. (5.204)',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O394="","",O397*O394*(O395^2)/2*SQRT((O387+O386)/(O387-O386)))', 'cell': 'O399'},
       'accuracy': 4},
    'lws_n6'
    : {'view': True, 'header': 'Lws  N6', 'dimension': '',
       'comment': 'ф. (5.57):\nУровень звуковой мощности, генерируемой потоком в кольцевом канале 1\n',
       'group_name': 'Расчет аэродинамики для кольцевых каналов',
       'formula': {'expr': '=IF(O399="","",10*LOG10(O399/(10^(-12))))', 'cell': 'O400'}, 'accuracy': 4},

    'udelnyj_obem_m3_kg_out'
    : {'view': True, 'header': 'Удельный объем, м3/кг', 'dimension': 'м3/кг',
       'comment': 'Удельный объем при заданной температуре и атмосферном давлении', 'accuracy': 3,
       'group_name': 'Расчет реактивной силы'},

    'massovyj_rashod_kg_s_out'
    : {'view': True, 'header': 'Массовый расход, кг/с', 'dimension': 'кг/с', 'comment': '', 'accuracy': 3,
       'group_name': 'Расчет реактивной силы'},
    'diametr_shg_m_out'
    : {'view': True, 'header': 'Диаметр ШГ, м', 'dimension': 'м', 'comment': '', 'accuracy': 3,
       'group_name': 'Расчет реактивной силы'},
    'koefficient_treniya_out'
    : {'view': True, 'header': 'ξ  - Коэффициент трения', 'dimension': '', 'comment': '', 'accuracy': 3,
       'group_name': 'Расчет реактивной силы'},
    'atmosfernoe_davlenie_pa_out'
    : {'view': True, 'header': 'Атмосферное давление, Па', 'dimension': 'Па',
       'comment': 'Стандартное атмосферное давление (Па)',
       'accuracy': 3, 'group_name': 'Расчет реактивной силы'},

}

ins = {'edinica_rashoda_imya': 'Промежуточные расчеты',
       'molyarnaya_massa_sredy_kg_mol': 'Промежуточные расчеты',
       'plotnost_sredy_kg_m3': 'Промежуточные расчеты',
       'skorost_para_iz_truby_m_s': 'Промежуточные расчеты',
       'v_skorost_mezhdu_plastinami_m_s': 'Промежуточные расчеты',
       'plotnost_rho_po_rashodu_i_geometrii': 'Промежуточные расчеты',
       'epsilon_1': 'Промежуточные расчеты',
       'k': 'Промежуточные расчеты',
       'y_1': 'Промежуточные расчеты',
       'y': 'Промежуточные расчеты',
       'λ': 'Промежуточные расчеты',
       'ploschad_vyhoda_shg_m2': 'Отдельное окно расчета',
       'skorost_na_vyhode_shg_m_s': 'Отдельное окно расчета',
       'r_reaktivnye_sily_n': 'Отдельное окно расчета',
       'sreda_2': 'Дроссельный блок',
       'rashod_sredy_g_kg_s': 'Дроссельный блок',
       'temperatura_sredy_s_2': 'Дроссельный блок',
       'davlenie_na_vhode_v_shg_pi_abs_mpa': 'Дроссельный блок',
       'davlenie_na_vyhode_iz_shg_pe_mpa': 'Дроссельный блок',
       'kriticheskaya_skorost_skr_m_s': 'Дроссельный блок',
       'gazovaya_postoyannaya_m2_s2_k': 'Дроссельный блок',
       'znachenie_p_drosselnogo_bloka': 'Дроссельный блок',
       'koeffcient_adiabaty': 'Дроссельный блок',
       'kolichestvo_stupenej_drosselirovaniya_j': 'Параметры дроссельного блока',
       'maksimalnoe_kolichestvo_otverstij_kmah_v_drosselnoj_reshetke_sht': 'Параметры дроссельного блока',
       'gradient_skorosti_w': 'Параметры дроссельного блока',
       'maksimalnyj_gradient_skorosti_wmax': 'Параметры дроссельного блока',
       'rekomenduemoe_nachalnoe_znachenie_w': 'Параметры дроссельного блока',
       'otnositelnyj_perepad_davleniya_na_poslednej_reshetke': 'Параметры потока в дроссельном блоке',
       'stupeni_n1': 'Параметры потока в дроссельном блоке',
       'perepad_davlenij_n1': 'Параметры потока в дроссельном блоке',
       'gazodinamicheskaya_funkciya_rashoda_q_n1': 'Параметры потока в дроссельном блоке',
       'oblast_n1': 'Параметры потока в дроссельном блоке',
       'stupeni_n2': 'Параметры потока в дроссельном блоке',
       'perepad_davlenij_n2': 'Параметры потока в дроссельном блоке',
       'gazodinamicheskaya_funkciya_rashoda_q_n2': 'Параметры потока в дроссельном блоке',
       'oblast_n2': 'Параметры потока в дроссельном блоке',
       'stupeni_n3': 'Параметры потока в дроссельном блоке',
       'perepad_davlenij_n3': 'Параметры потока в дроссельном блоке',
       'gazodinamicheskaya_funkciya_rashoda_q_n3': 'Параметры потока в дроссельном блоке',
       'oblast_n3': 'Параметры потока в дроссельном блоке',
       'stupeni_n4': 'Параметры потока в дроссельном блоке',
       'perepad_davlenij_n4': 'Параметры потока в дроссельном блоке',
       'gazodinamicheskaya_funkciya_rashoda_q_n4': 'Параметры потока в дроссельном блоке',
       'oblast_n4': 'Параметры потока в дроссельном блоке',
       'stupeni_n5': 'Параметры потока в дроссельном блоке',
       'perepad_davlenij_n5': 'Параметры потока в дроссельном блоке',
       'gazodinamicheskaya_funkciya_rashoda_q_n5': 'Параметры потока в дроссельном блоке',
       'oblast_n5': 'Параметры потока в дроссельном блоке',
       'stupeni_n6': 'Параметры потока в дроссельном блоке',
       'perepad_davlenij_n6': 'Параметры потока в дроссельном блоке',
       'gazodinamicheskaya_funkciya_rashoda_q_n6': 'Параметры потока в дроссельном блоке',
       'oblast_n6': 'Параметры потока в дроссельном блоке',
       'stupeni_n7': 'Параметры потока в дроссельном блоке',
       'perepad_davlenij_n7': 'Параметры потока в дроссельном блоке',
       'gazodinamicheskaya_funkciya_rashoda_q_n7': 'Параметры потока в дроссельном блоке',
       'oblast_n7': 'Параметры потока в дроссельном блоке',
       'stupeni_n8': 'Параметры потока в дроссельном блоке',
       'perepad_davlenij_n8': 'Параметры потока в дроссельном блоке',
       'gazodinamicheskaya_funkciya_rashoda_q_n8': 'Параметры потока в дроссельном блоке',
       'oblast_n8': 'Параметры потока в дроссельном блоке',
       'stupeni_n9': 'Параметры потока в дроссельном блоке',
       'perepad_davlenij_n9': 'Параметры потока в дроссельном блоке',
       'gazodinamicheskaya_funkciya_rashoda_q_n9': 'Параметры потока в дроссельном блоке',
       'oblast_n9': 'Параметры потока в дроссельном блоке',
       'stupeni_n10': 'Параметры потока в дроссельном блоке',
       'perepad_davlenij_n10': 'Параметры потока в дроссельном блоке',
       'gazodinamicheskaya_funkciya_rashoda_q_n10': 'Параметры потока в дроссельном блоке',
       'oblast_n10': 'Параметры потока в дроссельном блоке',
       'stupenin1_2_n1': 'Расчет геометрических параметров',
       'diametry_otverstij_mm_n1': 'Расчет геометрических параметров',
       'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n1': 'Расчет геометрических параметров',
       'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n1': 'Расчет геометрических параметров',
       'stupenin1_2_n2': 'Расчет геометрических параметров',
       'diametry_otverstij_mm_n2': 'Расчет геометрических параметров',
       'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n2': 'Расчет геометрических параметров',
       'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n2': 'Расчет геометрических параметров',
       'stupenin1_2_n3': 'Расчет геометрических параметров',
       'diametry_otverstij_mm_n3': 'Расчет геометрических параметров',
       'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n3': 'Расчет геометрических параметров',
       'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n3': 'Расчет геометрических параметров',
       'stupenin1_2_n4': 'Расчет геометрических параметров',
       'diametry_otverstij_mm_n4': 'Расчет геометрических параметров',
       'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n4': 'Расчет геометрических параметров',
       'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n4': 'Расчет геометрических параметров',
       'stupenin1_2_n5': 'Расчет геометрических параметров',
       'diametry_otverstij_mm_n5': 'Расчет геометрических параметров',
       'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n5': 'Расчет геометрических параметров',
       'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n5': 'Расчет геометрических параметров',
       'stupenin1_2_n6': 'Расчет геометрических параметров',
       'diametry_otverstij_mm_n6': 'Расчет геометрических параметров',
       'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n6': 'Расчет геометрических параметров',
       'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n6': 'Расчет геометрических параметров',
       'stupenin1_2_n7': 'Расчет геометрических параметров',
       'diametry_otverstij_mm_n7': 'Расчет геометрических параметров',
       'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n7': 'Расчет геометрических параметров',
       'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n7': 'Расчет геометрических параметров',
       'stupenin1_2_n8': 'Расчет геометрических параметров',
       'diametry_otverstij_mm_n8': 'Расчет геометрических параметров',
       'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n8': 'Расчет геометрических параметров',
       'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n8': 'Расчет геометрических параметров',
       'stupenin1_2_n9': 'Расчет геометрических параметров',
       'diametry_otverstij_mm_n9': 'Расчет геометрических параметров',
       'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n9': 'Расчет геометрических параметров',
       'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n9': 'Расчет геометрических параметров',
       'stupenin1_2_n10': 'Расчет геометрических параметров',
       'diametry_otverstij_mm_n10': 'Расчет геометрических параметров',
       'prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n10': 'Расчет геометрических параметров',
       'minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n10': 'Расчет геометрических параметров',
       'temperatura_k': 'Аэродинамика',
       'sa_ploschad_secheniya_shumoglushitelya_m2': 'Аэродинамика',
       'perimetr_m': 'Аэродинамика',
       'sk_ploschad_vyhodnogo_secheniya_korpusa_do_kryshki_kv_m': 'Аэродинамика',
       'da_vnutrennij_diametr_vyhlopa_iz_korpusa_m': 'Аэродинамика',
       'nezapolnennaya_ploschad_kv_m': 'Аэродинамика',
       'gidravlicheskij_diametr_m': 'Аэродинамика',
       'otnositelnaya_ploschad': 'Аэродинамика',
       'pd_srednij_skorostnoj_napor_na_vyhode_iz_schelevyh_kanalov': 'Аэродинамика',
       'kriticheskij_perepad_davlenij': 'Аэродинамика',
       'pk_izbytochnoe_davlenie_pod_kryshkoj_pa': 'Расчет давлений',
       'pa_izbytochnoe_davlenie_na_vyhode_iz_korpusa_za_stupenyu_zvukopogloscheniya_pa': 'Расчет давлений',
       'pa_absolyutnoe_davlenie_za_stupenyu_zvukopogloscheniya_pa': 'Расчет давлений',
       'pi3_davlenie_pered_stupenyu_zvukopogloscheniya_pa': 'Расчет давлений',
       'izbytochnoe_davlenie_pod_kryshkoj_ne_mozhet_prevyshat_15000_pa': 'Расчет давлений',
       'izbytochnoe_davlenie_na_vyhode_iz_korpusa_za_stupenyu_zvukopogloscheniya_ne_mozhet_prevyshat_15000_pa': 'Расчет давлений',
       'wa_skorost_na_vyhode_iz_korpusa_m_s': 'Расчет скоростей',
       'wk_skorost_na_vyhlope_v_atmosferu_m_s': 'Расчет скоростей',
       'ma_chislo_maha_na_vyhode_iz_korpusa': 'Расчет скоростей',
       'mk_chislo_maha_na_vyhlope_v_atmosferu': 'Расчет скоростей',
       'dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_bokovom_vyhlope_kn': 'Динамические нагрузки',
       'dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_osevom_vyhlope_kn': 'Динамические нагрузки',
       'dinamicheskaya_nagruzka_na_drosselnyj_blok_kn': 'Динамические нагрузки',
       'dinamicheskaya_nagruzka_na_stupen_zvukopogloscheniya_kn': 'Динамические нагрузки',
       'stupeni_n0': 'Давление за дроссельными решетками',
       'davlenie_za_reshetkami_mpa_n0': 'Давление за дроссельными решетками',
       'y_n0': 'Давление за дроссельными решетками',
       'perepad_davlenij_n0': 'Давление за дроссельными решетками',
       'n0': 'Давление за дроссельными решетками',
       'n0_2': 'Давление за дроссельными решетками',
       'n0_3': 'Давление за дроссельными решетками',
       'stupeni_n1_3': 'Давление за дроссельными решетками',
       'davlenie_za_reshetkami_mpa_n1': 'Давление за дроссельными решетками',
       'y_n1': 'Давление за дроссельными решетками',
       'perepad_davlenij_n1_2': 'Давление за дроссельными решетками',
       'n1': 'Давление за дроссельными решетками',
       'n1_2': 'Давление за дроссельными решетками',
       'n1_3': 'Давление за дроссельными решетками',
       'stupeni_n2_3': 'Давление за дроссельными решетками',
       'davlenie_za_reshetkami_mpa_n2': 'Давление за дроссельными решетками',
       'y_n2': 'Давление за дроссельными решетками',
       'perepad_davlenij_n2_2': 'Давление за дроссельными решетками',
       'n2': 'Давление за дроссельными решетками',
       'n2_2': 'Давление за дроссельными решетками',
       'n2_3': 'Давление за дроссельными решетками',
       'stupeni_n3_3': 'Давление за дроссельными решетками',
       'davlenie_za_reshetkami_mpa_n3': 'Давление за дроссельными решетками',
       'y_n3': 'Давление за дроссельными решетками',
       'perepad_davlenij_n3_2': 'Давление за дроссельными решетками',
       'n3': 'Давление за дроссельными решетками',
       'n3_2': 'Давление за дроссельными решетками',
       'n3_3': 'Давление за дроссельными решетками',
       'stupeni_n4_3': 'Давление за дроссельными решетками',
       'davlenie_za_reshetkami_mpa_n4': 'Давление за дроссельными решетками',
       'y_n4': 'Давление за дроссельными решетками',
       'perepad_davlenij_n4_2': 'Давление за дроссельными решетками',
       'n4': 'Давление за дроссельными решетками',
       'n4_2': 'Давление за дроссельными решетками',
       'n4_3': 'Давление за дроссельными решетками',
       'stupeni_n5_3': 'Давление за дроссельными решетками',
       'davlenie_za_reshetkami_mpa_n5': 'Давление за дроссельными решетками',
       'y_n5': 'Давление за дроссельными решетками',
       'perepad_davlenij_n5_2': 'Давление за дроссельными решетками',
       'n5': 'Давление за дроссельными решетками',
       'n5_2': 'Давление за дроссельными решетками',
       'n5_3': 'Давление за дроссельными решетками',
       'stupeni_n6_3': 'Давление за дроссельными решетками',
       'davlenie_za_reshetkami_mpa_n6': 'Давление за дроссельными решетками',
       'y_n6': 'Давление за дроссельными решетками',
       'perepad_davlenij_n6_2': 'Давление за дроссельными решетками',
       'n6': 'Давление за дроссельными решетками',
       'n6_2': 'Давление за дроссельными решетками',
       'n6_3': 'Давление за дроссельными решетками',
       'stupeni_n7_3': 'Давление за дроссельными решетками',
       'davlenie_za_reshetkami_mpa_n7': 'Давление за дроссельными решетками',
       'y_n7': 'Давление за дроссельными решетками',
       'perepad_davlenij_n7_2': 'Давление за дроссельными решетками',
       'n7': 'Давление за дроссельными решетками',
       'n7_2': 'Давление за дроссельными решетками',
       'n7_3': 'Давление за дроссельными решетками',
       'stupeni_n8_3': 'Давление за дроссельными решетками',
       'davlenie_za_reshetkami_mpa_n8': 'Давление за дроссельными решетками',
       'y_n8': 'Давление за дроссельными решетками',
       'perepad_davlenij_n8_2': 'Давление за дроссельными решетками',
       'n8': 'Давление за дроссельными решетками',
       'n8_2': 'Давление за дроссельными решетками',
       'n8_3': 'Давление за дроссельными решетками',
       'stupeni_n9_3': 'Давление за дроссельными решетками',
       'davlenie_za_reshetkami_mpa_n9': 'Давление за дроссельными решетками',
       'y_n9': 'Давление за дроссельными решетками',
       'perepad_davlenij_n9_2': 'Давление за дроссельными решетками',
       'n9': 'Давление за дроссельными решетками',
       'n9_2': 'Давление за дроссельными решетками',
       'n9_3': 'Давление за дроссельными решетками',
       'stupeni_n10_3': 'Давление за дроссельными решетками',
       'davlenie_za_reshetkami_mpa_n10': 'Давление за дроссельными решетками',
       'y_n10': 'Давление за дроссельными решетками',
       'perepad_davlenij_n10_2': 'Давление за дроссельными решетками',
       'n10': 'Давление за дроссельными решетками',
       'n10_2': 'Давление за дроссельными решетками',
       'n10_3': 'Давление за дроссельными решетками',
       'obtekateli': 'Расчет аэродинамики для кольцевых каналов',
       'r_gazovaya_postoyannaya_m2s2_k': 'Расчет аэродинамики для кольцевых каналов',
       'k_pokazatel_adiabaty': 'Расчет аэродинамики для кольцевых каналов',
       't_absolyutnaya_temperatura_pered_glushitelem_k': 'Расчет аэродинамики для кольцевых каналов',
       'g_rashod_sredy_kg_s': 'Расчет аэродинамики для кольцевых каналов',
       'd_vnutrennij_diametr_shg_m': 'Расчет аэродинамики для кольцевых каналов',
       'pat_atmosfernoe_davlenie_pa': 'Расчет аэродинамики для кольцевых каналов',
       'ss_summarnaya_ploschad_vseh_kanalov_m2': 'Расчет аэродинамики для кольцевых каналов',
       'summ_diam': 'Расчет аэродинамики для кольцевых каналов',
       'f_otnositelnaya_ploschad': 'Расчет аэродинамики для кольцевых каналов',
       'l_dlina_kanalov_m': 'Расчет аэродинамики для кольцевых каналов',
       'pa_pa': 'Расчет аэродинамики для кольцевых каналов',
       'ptr_pa': 'Расчет аэродинамики для кольцевых каналов',
       'pi3_davlenie_pered_stupenyu_zvukopogloscheniya_pa_2': 'Расчет аэродинамики для кольцевых каналов',
       'maksimalnaya_skorost_mezhdu_kasset_m_s': 'Расчет аэродинамики для кольцевых каналов',
       'v_aero': 'Расчет аэродинамики для кольцевых каналов',
       'plotnost_rho_po_idealnomu_gazu': 'Расчет аэродинамики для кольцевых каналов',
       'r_vnutrennij_radius_m_n1': 'Расчет аэродинамики для кольцевых каналов',
       'r_naruzhnyj_radius_m_n1': 'Расчет аэродинамики для кольцевых каналов',
       'dh_gidravlicheskij_diametr_m_n1': 'Расчет аэродинамики для кольцевых каналов',
       'd_shirina_kanala_m_n1': 'Расчет аэродинамики для кольцевых каналов',
       'f_ploschad_kanala_m2_n1': 'Расчет аэродинамики для кольцевых каналов',
       'f_dh_0_5_n1': 'Расчет аэродинамики для кольцевых каналов',
       'h_srednyaya_tolschina_plastin_m_n1': 'Расчет аэродинамики для кольцевых каналов',
       'pd_skorostnoj_napor_na_vyhode_pa_n1': 'Расчет аэродинамики для кольцевых каналов',
       'g_rashod_v_kanale_kg_s_n1': 'Расчет аэродинамики для кольцевых каналов',
       'w_skorost_v_kanale_m_s_n1': 'Расчет аэродинамики для кольцевых каналов',
       'm_chislo_maha_v_kanale_n1': 'Расчет аэродинамики для кольцевых каналов',
       'k_m_n1': 'Расчет аэродинамики для кольцевых каналов',
       'ds_n1': 'Расчет аэродинамики для кольцевых каналов',
       'ws_moschnost_shuma_na_vyhode_kanala_vt_n1': 'Расчет аэродинамики для кольцевых каналов',
       'lws_n1': 'Расчет аэродинамики для кольцевых каналов',
       'r_vnutrennij_radius_m_n2': 'Расчет аэродинамики для кольцевых каналов',
       'r_naruzhnyj_radius_m_n2': 'Расчет аэродинамики для кольцевых каналов',
       'dh_gidravlicheskij_diametr_m_n2': 'Расчет аэродинамики для кольцевых каналов',
       'd_shirina_kanala_m_n2': 'Расчет аэродинамики для кольцевых каналов',
       'f_ploschad_kanala_m2_n2': 'Расчет аэродинамики для кольцевых каналов',
       'f_dh_0_5_n2': 'Расчет аэродинамики для кольцевых каналов',
       'h_srednyaya_tolschina_plastin_m_n2': 'Расчет аэродинамики для кольцевых каналов',
       'pd_skorostnoj_napor_na_vyhode_pa_n2': 'Расчет аэродинамики для кольцевых каналов',
       'g_rashod_v_kanale_kg_s_n2': 'Расчет аэродинамики для кольцевых каналов',
       'w_skorost_v_kanale_m_s_n2': 'Расчет аэродинамики для кольцевых каналов',
       'm_chislo_maha_v_kanale_n2': 'Расчет аэродинамики для кольцевых каналов',
       'k_m_n2': 'Расчет аэродинамики для кольцевых каналов',
       'ds_n2': 'Расчет аэродинамики для кольцевых каналов',
       'ws_moschnost_shuma_na_vyhode_kanala_vt_n2': 'Расчет аэродинамики для кольцевых каналов',
       'lws_n2': 'Расчет аэродинамики для кольцевых каналов',
       'r_vnutrennij_radius_m_n3': 'Расчет аэродинамики для кольцевых каналов',
       'r_naruzhnyj_radius_m_n3': 'Расчет аэродинамики для кольцевых каналов',
       'dh_gidravlicheskij_diametr_m_n3': 'Расчет аэродинамики для кольцевых каналов',
       'd_shirina_kanala_m_n3': 'Расчет аэродинамики для кольцевых каналов',
       'f_ploschad_kanala_m2_n3': 'Расчет аэродинамики для кольцевых каналов',
       'f_dh_0_5_n3': 'Расчет аэродинамики для кольцевых каналов',
       'h_srednyaya_tolschina_plastin_m_n3': 'Расчет аэродинамики для кольцевых каналов',
       'pd_skorostnoj_napor_na_vyhode_pa_n3': 'Расчет аэродинамики для кольцевых каналов',
       'g_rashod_v_kanale_kg_s_n3': 'Расчет аэродинамики для кольцевых каналов',
       'w_skorost_v_kanale_m_s_n3': 'Расчет аэродинамики для кольцевых каналов',
       'm_chislo_maha_v_kanale_n3': 'Расчет аэродинамики для кольцевых каналов',
       'k_m_n3': 'Расчет аэродинамики для кольцевых каналов',
       'ds_n3': 'Расчет аэродинамики для кольцевых каналов',
       'ws_moschnost_shuma_na_vyhode_kanala_vt_n3': 'Расчет аэродинамики для кольцевых каналов',
       'lws_n3': 'Расчет аэродинамики для кольцевых каналов',
       'r_vnutrennij_radius_m_n4': 'Расчет аэродинамики для кольцевых каналов',
       'r_naruzhnyj_radius_m_n4': 'Расчет аэродинамики для кольцевых каналов',
       'dh_gidravlicheskij_diametr_m_n4': 'Расчет аэродинамики для кольцевых каналов',
       'd_shirina_kanala_m_n4': 'Расчет аэродинамики для кольцевых каналов',
       'f_ploschad_kanala_m2_n4': 'Расчет аэродинамики для кольцевых каналов',
       'f_dh_0_5_n4': 'Расчет аэродинамики для кольцевых каналов',
       'h_srednyaya_tolschina_plastin_m_n4': 'Расчет аэродинамики для кольцевых каналов',
       'pd_skorostnoj_napor_na_vyhode_pa_n4': 'Расчет аэродинамики для кольцевых каналов',
       'g_rashod_v_kanale_kg_s_n4': 'Расчет аэродинамики для кольцевых каналов',
       'w_skorost_v_kanale_m_s_n4': 'Расчет аэродинамики для кольцевых каналов',
       'm_chislo_maha_v_kanale_n4': 'Расчет аэродинамики для кольцевых каналов',
       'k_m_n4': 'Расчет аэродинамики для кольцевых каналов',
       'ds_n4': 'Расчет аэродинамики для кольцевых каналов',
       'ws_moschnost_shuma_na_vyhode_kanala_vt_n4': 'Расчет аэродинамики для кольцевых каналов',
       'lws_n4': 'Расчет аэродинамики для кольцевых каналов',
       'r_vnutrennij_radius_m_n5': 'Расчет аэродинамики для кольцевых каналов',
       'r_naruzhnyj_radius_m_n5': 'Расчет аэродинамики для кольцевых каналов',
       'dh_gidravlicheskij_diametr_m_n5': 'Расчет аэродинамики для кольцевых каналов',
       'd_shirina_kanala_m_n5': 'Расчет аэродинамики для кольцевых каналов',
       'f_ploschad_kanala_m2_n5': 'Расчет аэродинамики для кольцевых каналов',
       'f_dh_0_5_n5': 'Расчет аэродинамики для кольцевых каналов',
       'h_srednyaya_tolschina_plastin_m_n5': 'Расчет аэродинамики для кольцевых каналов',
       'pd_skorostnoj_napor_na_vyhode_pa_n5': 'Расчет аэродинамики для кольцевых каналов',
       'g_rashod_v_kanale_kg_s_n5': 'Расчет аэродинамики для кольцевых каналов',
       'w_skorost_v_kanale_m_s_n5': 'Расчет аэродинамики для кольцевых каналов',
       'm_chislo_maha_v_kanale_n5': 'Расчет аэродинамики для кольцевых каналов',
       'k_m_n5': 'Расчет аэродинамики для кольцевых каналов',
       'ds_n5': 'Расчет аэродинамики для кольцевых каналов',
       'ws_moschnost_shuma_na_vyhode_kanala_vt_n5': 'Расчет аэродинамики для кольцевых каналов',
       'lws_n5': 'Расчет аэродинамики для кольцевых каналов',
       'r_vnutrennij_radius_m_n6': 'Расчет аэродинамики для кольцевых каналов',
       'r_naruzhnyj_radius_m_n6': 'Расчет аэродинамики для кольцевых каналов',
       'dh_gidravlicheskij_diametr_m_n6': 'Расчет аэродинамики для кольцевых каналов',
       'd_shirina_kanala_m_n6': 'Расчет аэродинамики для кольцевых каналов',
       'f_ploschad_kanala_m2_n6': 'Расчет аэродинамики для кольцевых каналов',
       'f_dh_0_5_n6': 'Расчет аэродинамики для кольцевых каналов',
       'h_srednyaya_tolschina_plastin_m_n6': 'Расчет аэродинамики для кольцевых каналов',
       'pd_skorostnoj_napor_na_vyhode_pa_n6': 'Расчет аэродинамики для кольцевых каналов',
       'g_rashod_v_kanale_kg_s_n6': 'Расчет аэродинамики для кольцевых каналов',
       'w_skorost_v_kanale_m_s_n6': 'Расчет аэродинамики для кольцевых каналов',
       'm_chislo_maha_v_kanale_n6': 'Расчет аэродинамики для кольцевых каналов',
       'k_m_n6': 'Расчет аэродинамики для кольцевых каналов',
       'ds_n6': 'Расчет аэродинамики для кольцевых каналов',
       'ws_moschnost_shuma_na_vyhode_kanala_vt_n6': 'Расчет аэродинамики для кольцевых каналов',
       'lws_n6': 'Расчет аэродинамики для кольцевых каналов',
       'g_rashod_sredy_kg_s_2': 'Расчет выхлопной части',
       'k_koefficient_adiabaty': 'Расчет выхлопной части',
       'r_individualnaya_gazovaya_postoyannaya_m2s2_k': 'Расчет выхлопной части',
       't_temperatura_sredy_k': 'Расчет выхлопной части',
       'pat_atmosfernoe_davlenie_pa_2': 'Расчет выхлопной части',
       'd_vnutrennij_diametr_korpusa_stupeni_zvukopogloscheniya_m': 'Расчет выхлопной части',
       'da_vnutrennij_diametr_vyhlopa_m': 'Расчет выхлопной части',
       'hk_osevoe_rasstoyanie_ot_vyhodnogo_secheniya_korpusa_do_kryshki_m': 'Расчет выхлопной части',
       'sk_ploschad_vyhodnogo_secheniya_kanala_korpusa_do_kryshki_m2': 'Расчет выхлопной части',
       'sa': 'Расчет выхлопной части',
       'pk_izbytochnoe_davlenie_pod_kryshkoj_pa_2': 'Расчет выхлопной части',
       'pa_izbytochnoe_davlenie_na_vyhode_iz_korpusa_za_stupenyu_zvukopogloscheniya_pa_2': 'Расчет выхлопной части',
       'pa_absolyutnoe_davlenie_za_stupenyu_zvukopogloscheniya_pa_2': 'Расчет выхлопной части',
       'pk': 'Расчет выхлопной части',
       'wa_skorost_na_vyhode_iz_korpusa_m_s_2': 'Расчет выхлопной части',
       'wk_skorost_na_vyhlope_v_atmosferu_m_s_2': 'Расчет выхлопной части',
       'ma_chislo_maha_na_vyhode_iz_korpusa_2': 'Расчет выхлопной части',
       'mk_chislo_maha_na_vyhlope_v_atmosferu_2': 'Расчет выхлопной части',
       'k_ma': 'Расчет выхлопной части',
       'k_mk': 'Расчет выхлопной части',
       'wa_moschnost_shuma_na_vyhode_iz_korpusa_vt': 'Расчет выхлопной части',
       'wk_moschnost_shuma_na_vyhode_iz_pod_kryshki_vt': 'Расчет выхлопной части',
       'lwa_uzm_generiruemyj_istecheniem_iz_korpusa_db': 'Расчет выхлопной части',
       'lwk_uzm_generiruemyj_istecheniem_iz_pod_kryshki_db': 'Расчет выхлопной части',
       'dinamicheskaya_nagruzka_na_drosselnyj_blok_kn_2': 'Динамические нагрузки',
       'dinamicheskaya_nagruzka_na_stupen_zvukopogloscheniya_kn_2': 'Динамические нагрузки',
       'dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_bokovom_vyhlope_kn_2': 'Динамические нагрузки',
       'dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_osevom_vyhlope_kn_2': 'Динамические нагрузки',
       'davlenie_na_dnische_drosselnogo_bloka_mpa': 'Динамические нагрузки',
       }

GROUPS = {
    'Промежуточные расчеты': False,
    'Расчет аэродинамики для кольцевых каналов': False,
    'Отдельное окно расчета': False,
    'Дроссельный блок': False,
    'Параметры дроссельного блока': False,
    'Параметры потока в дроссельном блоке': True,
    'Расчет геометрических параметров': True,
    'Аэродинамика': True,
    'Расчет давлений': False,
    'Расчет скоростей': False,
    'Динамические нагрузки': True,
    'Давление за дроссельными решетками': False,
    'Расчет выхлопной части': False,
    'Расчет реактивной силы': True
}
