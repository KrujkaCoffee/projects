import math
from collections import OrderedDict
from typing import Optional
def normalize_params(params: dict) -> dict:
    """Normalize keys with non-ASCII symbols to safe ASCII aliases (e.g., ρ→rho, ε→epsilon, λ→lambda_friction)."""
    aliases = {
        'ρ': 'rho',
        'λ': 'lambda_friction',
        'ε': 'epsilon',
        'ε_1': 'epsilon_1',
        'ε_2': 'epsilon_2',
        'π': 'pi',
        'diametr_shg_m':'d_vnutrennij_diametr_shg_m',
        'davlenie_na_vhode_v_shg_ri_abs_mpa':'davlenie_na_vhode_v_shg_pi_abs_mpa',

    }
    normalized = dict(params)
    for k, v in list(params.items()):
        if k in aliases and aliases[k] not in params:
            normalized[aliases[k]] = v
    return normalized


# --- Константы для расчетов ---
CONSTANTS = {
    'R_universal': 8.314459,       # Дж/(моль·К)
    'gravity': 9.81,               # м/с²
    'pi': 3.141592653589793,       # число Пи
    'atm_pressure': 101325,        # Па
    'kelvin_shift': 273.15,        # для перевода °C → K
    'safety_factor': 1.2,          # коэффициент запаса
    'compressor_efficiency': 0.65, # η компрессора
    'compressor_pressure_loss': 0.3,
}


def power(x, y):
    """Аналог Excel POWER(x,y)."""
    return None if x is None or y is None else math.pow(x, y)



def roundup(x: float, n: int = 0) -> float:
    """
    Excel ROUNDUP(x, n)
    Округление вверх до n знаков после запятой.
    """
    factor = 10 ** n
    return math.ceil(x * factor) / factor

def rounddown(x: float, n: int = 0) -> float:
    """
    Excel ROUNDDOWN(x, n)
    Округление вниз до n знаков после запятой.
    """
    factor = 10 ** n
    return math.floor(x * factor) / factor



"""
Функции расчёта для диапазона M5–M400.
- Формулы Excel переписаны в Python (IF → тернарные, AND/OR → операторы).
- Ячейки Excel заменены на читаемые ключи params.
- Магические числа заменены на params.get(...).
"""
def calc_edinica_rashoda_imya(params):
    """
    Excel M5 / O5
    Формула (Excel): =IF(E10="т/ч","Расход среды G, т/ч",IF(E10="кг/с","Расход среды G, кг/с"))
    """
    return f"Расход среды G, {params['edinica_rashoda']}"


def calc_molyarnaya_massa_sredy_kg_mol(params):
    """
    Excel M6 / O6
    Формула (Excel): =8.314459/O29
    """
    return (8.314459/params['gazovaya_postoyannaya_m2_s2_k'])

def calc_plotnost_sredy_kg_m3(params):
    """
    Excel M7 / O7
    Формула (Excel): =O26*O6/(8.314459*O135)*1000000
    """
    return (params['davlenie_na_vhode_v_shg_pi_abs_mpa']*params['molyarnaya_massa_sredy_kg_mol']/(8.314459*params['temperatura_k'])*1000000)

def calc_skorost_para_iz_truby_m_s(params):
    """
    Excel M8 / O8
    Формула (Excel): =O24/(O7*(PI()*E36^2/4))
    """
    return (params['rashod_sredy_g_kg_s']/(params['plotnost_sredy_kg_m3']*(math.pi*params['vyhodnoj_vneshnij_diametr_m']**2/4)))

def calc_v_skorost_mezhdu_plastinami_m_s(params):
    """
    Расчёт скорости между пластинами (м/с).

    Excel ссылка: M10 / O10
    Формула из Excel:
    =(O24*O29*O135) /
     ((((O24^2*O29*O135*E62*E29) / (2*O140*O141^0.5)^2) + O152^2)^0.5 * O140)
    """

    numerator = (
        params["rashod_sredy_g_kg_s"]
        * params["gazovaya_postoyannaya_m2_s2_k"]
        * params["temperatura_k"]
    )

    denominator_part1 = (
        params["rashod_sredy_g_kg_s"] ** 2
        * params["gazovaya_postoyannaya_m2_s2_k"]
        * params["temperatura_k"]
        * params["koefficient_treniya"]
        * params["dlina_oblicovannyh_kanalov_m"]
    )

    denominator_part2 = (
        (2 * params["nezapolnennaya_ploschad_kv_m"] * params["gidravlicheskij_diametr_m"] ** 0.5) ** 2
    )

    denominator = (
        ((denominator_part1 / denominator_part2)
        + params["pa_absolyutnoe_davlenie_za_stupenyu_zvukopogloscheniya_pa"] ** 2) ** 0.5
        * params["nezapolnennaya_ploschad_kv_m"]
    )

    return numerator / denominator

def calc_plotnost_rho_po_rashodu_i_geometrii(params):
    """
    Excel M11 / O11
    ρ по расходу + геометрии + сопротивлению
    Формула (Excel): =(((O24^2*O29*O135*E62*E29)/(2*O140*O141^0.5)^2)+E63^2)^0.5/(O29*O135)
    """
    g = params['rashod_sredy_g_kg_s']
    R = params['gazovaya_postoyannaya_m2_s2_k']
    T = params['temperatura_k']
    xi = params['koefficient_treniya']
    L  = params['dlina_oblicovannyh_kanalov_m']
    A  = params['nezapolnennaya_ploschad_kv_m']
    Dh = params['gidravlicheskij_diametr_m']
    p_atm = params['atmosfernoe_davlenie_pa']

    denom = (2.0 * A * (Dh ** 0.5)) ** 2
    under_sqrt = (g**2 * R * T * xi * L) / denom + p_atm**2
    rho = math.sqrt(under_sqrt) / (R * T)
    return rho


def calc_epsilon_1(params):
    """
    Excel M12 / O12
    Формула (Excel): =(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1))
    """
    return ((1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1)))

def calc_k(params):
    """
    Расчёт коэффициента k.

    Excel ссылка: M13 / O13
    Формула из Excel:
    =($O$31+1)/(2*$O$31) * (O24*O28) / O12
    """

    numerator = (
        (params["koeffcient_adiabaty"] + 1)
        / (2 * params["koeffcient_adiabaty"])
        * (params["rashod_sredy_g_kg_s"] * params["kriticheskaya_skorost_skr_m_s"])
    )

    denominator = params["v_skorost_mezhdu_plastinami_m_s"]

    return numerator / denominator


def calc_y_1(params):
    """
    Excel M14 / O14
    Формула (Excel): =((($O$31+1)/2)^(1/($O$31-1)))/(1-($O$31-1)/($O$31+1))
    """
    return ((((params['koeffcient_adiabaty']+1)/2)**(1/(params['koeffcient_adiabaty']-1)))/(1-(params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))

def calc_y(params):
    """
    Excel M15 / O15
    Формула (Excel): =O13/(O92*O174)
    """
    return (params['k']/(params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n1']*params['davlenie_za_reshetkami_mpa_n0']))

def calc_λ(params):
    """
    Excel M16 / O16
    Формула (Excel): =(-1+(1+4*(($O$31-1)/($O$31+1))*O12^2*O15^2)^0.5)/(2*(($O$31-1)/($O$31+1))*O12*O15)
    """
    return ((-1+(1+4*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']**2*params['y']**2)**0.5)/(2*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']*params['y']))

def calc_ploschad_vyhoda_shg_m2(params):
    """
    Excel M18 / O18
    Формула (Excel): =PI()*E59^2/4
    """
    return (math.pi*params['diametr_shg_m']**2/4)

def calc_skorost_na_vyhode_shg_m_s(params):
    """
    Excel M19 / O19
    Формула (Excel): =E58*E57/O18
    """
    return (params['massovyj_rashod_kg_s']*params['udelnyj_obem_m3_kg']/params['ploschad_vyhoda_shg_m2'])

def calc_r_reaktivnye_sily_n(params):
    """
    Excel M20 / O20
    Формула (Excel): =O19^2*O18/E57
    """
    return (params['skorost_na_vyhode_shg_m_s']**2*params['ploschad_vyhoda_shg_m2']/params['udelnyj_obem_m3_kg'])

def calc_sreda_2(params):
    """
    Excel M23 / O23
    Формула (Excel): =E9
    """
    return (params['sreda'])


def calc_rashod_sredy_g_kg_s(params: dict) -> float:
    """
    Расчет расхода среды в кг/с.

    Excel M24 / O24
    Формула: =IF(E10="кг/с",E11,IF(E10="т/ч",ROUNDUP(E11*1000/3600,2)))

    Args:
        params: Словарь с входными параметрами, должен содержать:
            - edinica_rashoda: единица расхода ("т/ч" или "кг/с")
            - rashod: значение расхода

    Returns:
        float: Расход в кг/с

    Raises:
        ValueError: Если единица расхода неизвестна или отсутствуют необходимые параметры
    """
    # Проверка наличия необходимых параметров
    if 'edinica_rashoda' not in params or 'rashod' not in params:
        raise ValueError("Отсутствуют необходимые параметры: edinica_rashoda или rashod")

    # Получение значений
    edinica = params['edinica_rashoda']
    rashod = params['rashod']

    # Расчет в зависимости от единицы измерения
    if edinica == "кг/с":
        return rashod
    elif edinica == "т/ч":
        return roundup(rashod * 1000 / 3600, 2)
    else:
        raise ValueError(f"Неизвестная единица расхода: {edinica}. Ожидается 'т/ч' или 'кг/с'")


def calc_temperatura_sredy_s_2(params):
    """
    Excel M25 / O25
    Формула (Excel): =E12
    """
    return (params['temperatura_sredy_s'])

def calc_davlenie_na_vhode_v_shg_pi_abs_mpa(params):
    """
    Excel M26 / O26
    Формула (Excel): =E13
    """
    return (params['davlenie_na_vhode_v_shg_ri_abs_mpa'])

def calc_davlenie_na_vyhode_iz_shg_pe_mpa(params):
    """
    Excel M27 / O27
    Формула (Excel): =O153*10^-6
    """
    return (params['pi3_davlenie_pered_stupenyu_zvukopogloscheniya_pa']*10**-6)

def calc_kriticheskaya_skorost_skr_m_s(params):
    """
    Excel M28 / O28
    Формула (Excel): =(2*O29*(E12+273)*($O$31/($O$31+1)))^0.5
    """
    return ((2*params['gazovaya_postoyannaya_m2_s2_k']*(params['temperatura_sredy_s']+params.get('zero_celsius_k', 273.15))*(params['koeffcient_adiabaty']/(params['koeffcient_adiabaty']+1)))**0.5)

def calc_gazovaya_postoyannaya_m2_s2_k(params):
    """
    Excel M29 / O29
    Формула (Excel): =IF(E9="Пар","461,5",IF(E9="Природный газ","508",IF(E9="Воздух","287",IF(E9="Углекислый газ (СО2)","188,9",IF(E9="Азот (N2)","296,8",IF(E9="Кислород (O2)","259,7",IF(E9="Аргон (Ar)",208)))))))
    """
    return (((461) if (params['sreda']=="Пар") else (5)))

def calc_znachenie_p_drosselnogo_bloka(params):
    """
    Excel M30 / O30
    Формула (Excel): =E13/O27
    """
    return (params['davlenie_na_vhode_v_shg_ri_abs_mpa']/params['davlenie_na_vyhode_iz_shg_pe_mpa'])

def calc_koeffcient_adiabaty(params):
    """
    Excel M31 / O31
    Формула (Excel): =IF(E9="Пар","1,3",IF(E9="Природный газ","1,4",IF(E9="Воздух","1,4",IF(E9="Углекислый газ (СО2)","1,3",IF(E9="Азот (N2)","1,4",IF(E9="Кислород (O2)","1,4",IF(E9="Аргон (Ar)",1.67)))))))
    """
    mapping = {
        "Пар": 1.3,
        "Природный газ": 1.4,
        "Воздух": 1.4,
        "Углекислый газ (СО2)": 1.3,
        "Азот (N2)": 1.4,
        "Кислород (O2)": 1.4,
        "Аргон (Ar)": 1.67,
    }
    return mapping.get(params['sreda'], None)

def calc_kolichestvo_stupenej_drosselirovaniya_j(params):
    """
    Excel M34 / O34
    Формула (Excel): =E17
    """
    return (params['kolichestvo_stupenej_drosselirovaniya_sht'])

def calc_maksimalnoe_kolichestvo_otverstij_kmah_v_drosselnoj_reshetke_sht(params):
    """
    Excel M35 / O35
    Формула (Excel): =E18
    """
    return (params['maksimalnoe_kolichestvo_otverstij_sht'])

def calc_gradient_skorosti_w(params):
    """
    Excel M38 / O38
    Формула (Excel): =IF($E$17=1,E19,ROUND(O40-0.01,2))
    """
    return (((params['pokazatel_gradienta']) if (params['kolichestvo_stupenej_drosselirovaniya_sht']==1) else (round(params['rekomenduemoe_nachalnoe_znachenie_w']-0.01,2))))

def calc_maksimalnyj_gradient_skorosti_wmax(params):
    """
    Excel M39 / O39
    Формула (Excel): =IF(E17=1,"",O30^(2/(O34*(O34-1))))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_sht']==1) else (params['znachenie_p_drosselnogo_bloka']**(2/(params['kolichestvo_stupenej_drosselirovaniya_j']*(params['kolichestvo_stupenej_drosselirovaniya_j']-1))))))

def calc_rekomenduemoe_nachalnoe_znachenie_w(params):
    """
    Excel M40 / O40
    Формула (Excel): =IF(E17=1,"",O39^0.875)
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_sht']==1) else (params['maksimalnyj_gradient_skorosti_wmax']**0.875)))

def calc_otnositelnyj_perepad_davleniya_na_poslednej_reshetke(params):
    """
    Excel M42 / O42
    Формула (Excel): =(O38^((O34-1)/2))/(O30^(1/O34))
    """
    return ((params['gradient_skorosti_w']**((params['kolichestvo_stupenej_drosselirovaniya_j']-1)/2))/(params['znachenie_p_drosselnogo_bloka']**(1/params['kolichestvo_stupenej_drosselirovaniya_j'])))

def calc_stupeni_n1(params):
    """
    Excel M45 / O45
    Формула (Excel): 1
    """
    return (1)

def calc_perepad_davlenij_n1(params):
    """
    Excel M46 / O46
    Формула (Excel): =IF($O$34=1,$O$42,IF($O$34=2,O50/$O$38^($O$34-O45),IF($O$34=3,O54/$O$38^($O$34-O45),IF($O$34=4,O58/$O$34^($O$34-O45),IF($O$34=5,O62/$O$34^($O$34-O45),IF($O$34=6,O66/$O$34^($O$34-O45),IF($O$34=7,O70/$O$34^($O$34-O45),IF($O$34=8,O74/$O$34^($O$34-O45),IF($O$34=9,O78/$O$34^($O$34-O45),IF($O$34=10,O82/$O$34^($O$34-O45)))))))))))
    """
    return (((params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']) if (params['kolichestvo_stupenej_drosselirovaniya_j']==1) else (((params['perepad_davlenij_n2']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n1'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==2) else (((params['perepad_davlenij_n3']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n1'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==3) else (((params['perepad_davlenij_n4']/params['kolichestvo_stupenej_drosselirovaniya_j']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n1'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==4) else (((params['perepad_davlenij_n5']/params['kolichestvo_stupenej_drosselirovaniya_j']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n1'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==5) else (((params['perepad_davlenij_n6']/params['kolichestvo_stupenej_drosselirovaniya_j']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n1'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==6) else (((params['perepad_davlenij_n7']/params['kolichestvo_stupenej_drosselirovaniya_j']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n1'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==7) else (((params['perepad_davlenij_n8']/params['kolichestvo_stupenej_drosselirovaniya_j']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n1'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==8) else (((params['perepad_davlenij_n9']/params['kolichestvo_stupenej_drosselirovaniya_j']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n1'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==9) else (((params['perepad_davlenij_n10']/params['kolichestvo_stupenej_drosselirovaniya_j']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n1'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==10) else (None)))))))))))))))))))))

def calc_gazodinamicheskaya_funkciya_rashoda_q_n1(params):
    """
    Excel M47 / O47
    Формула (Excel): =IF(O46^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O46^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O46^(($O$31-1)/$O$31))),1)
    """
    return ((((params['perepad_davlenij_n1']**(1/params['koeffcient_adiabaty'])/(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1)))*math.sqrt((params['koeffcient_adiabaty']+1)/(params['koeffcient_adiabaty']-1)*(1-params['perepad_davlenij_n1']**((params['koeffcient_adiabaty']-1)/params['koeffcient_adiabaty'])))) if (params['perepad_davlenij_n1']**(1/params['koeffcient_adiabaty'])>(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1))) else (1)))

def calc_oblast_n1(params):
    """
    Excel M48 / O48
    Формула (Excel): =IF(AND(O46<1,O46>O144),"Дозвуковая область","Сверхзвуковая область")
    """
    return ((("Дозвуковая область") if ((params['perepad_davlenij_n1']<1 and params['perepad_davlenij_n1']>params['kriticheskij_perepad_davlenij'])) else ("Сверхзвуковая область")))

def calc_stupeni_n2(params):
    """
    Excel M49 / O49
    Формула (Excel): =IF($E$17>1,"2","")
    """
    return (((2) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>1) else (None)))

def calc_perepad_davlenij_n2(params):
    """
    Excel M50 / O50
    Формула (Excel): =IF(O34=1,"",IF(O34=2,O42,IF(O34=3,O54/(O38^(O34-O49)),IF(O34=4,O58/(O38^(O34-O49)),IF(O34=5,O62/(O38^(O34-O49)),IF(O34=6,O66/(O38^(O34-O49)),IF(O34=7,O70/(O38^(O34-O49)),IF(O34=8,O74/(O38^(O34-O49)),IF(O34=9,O78/(O38^(O34-O49)),IF(O34=10,O82/(O38^(O34-O49))))))))))))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']==1) else (((params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']) if (params['kolichestvo_stupenej_drosselirovaniya_j']==2) else (((params['perepad_davlenij_n3']/(params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n2']))) if (params['kolichestvo_stupenej_drosselirovaniya_j']==3) else (((params['perepad_davlenij_n4']/(params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n2']))) if (params['kolichestvo_stupenej_drosselirovaniya_j']==4) else (((params['perepad_davlenij_n5']/(params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n2']))) if (params['kolichestvo_stupenej_drosselirovaniya_j']==5) else (((params['perepad_davlenij_n6']/(params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n2']))) if (params['kolichestvo_stupenej_drosselirovaniya_j']==6) else (((params['perepad_davlenij_n7']/(params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n2']))) if (params['kolichestvo_stupenej_drosselirovaniya_j']==7) else (((params['perepad_davlenij_n8']/(params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n2']))) if (params['kolichestvo_stupenej_drosselirovaniya_j']==8) else (((params['perepad_davlenij_n9']/(params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n2']))) if (params['kolichestvo_stupenej_drosselirovaniya_j']==9) else (((params['perepad_davlenij_n10']/(params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n2']))) if (params['kolichestvo_stupenej_drosselirovaniya_j']==10) else (None)))))))))))))))))))))

def calc_gazodinamicheskaya_funkciya_rashoda_q_n2(params):
    """
    Excel M51 / O51
    Формула (Excel): =IF(O34=1,"",IF(O50^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O50^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O50^(($O$31-1)/$O$31))),1))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']==1) else ((((params['perepad_davlenij_n2']**(1/params['koeffcient_adiabaty'])/(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1)))*math.sqrt((params['koeffcient_adiabaty']+1)/(params['koeffcient_adiabaty']-1)*(1-params['perepad_davlenij_n2']**((params['koeffcient_adiabaty']-1)/params['koeffcient_adiabaty'])))) if (params['perepad_davlenij_n2']**(1/params['koeffcient_adiabaty'])>(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1))) else (1)))))

def calc_oblast_n2(params):
    """
    Excel M52 / O52
    Формула (Excel): =IF(O34=1,"",IF(AND(O50<1,O50>O144),"Дозвуковая область","Сверхзвуковая область"))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']==1)
             else ((("Дозвуковая область") if
                    ((params['perepad_davlenij_n2']<1 and params['perepad_davlenij_n2']>params['kriticheskij_perepad_davlenij']))
                    else ("Сверхзвуковая область")))))

def calc_stupeni_n3(params):
    """
    Excel M53 / O53
    Формула (Excel): =IF($E$17>2,"3","")
    """
    return (((3) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>2) else (None)))

def calc_perepad_davlenij_n3(params):
    """
    Excel M54 / O54
    Формула (Excel): =IF(O34<3,"",IF(O34=3,O42,IF(O34=4,O58/(O38^(O34-O53)),IF(O34=5,O62/(O38^(O34-O53)),IF(O34=6,O66/(O38^(O34-O53)),IF(O34=7,O70/(O38^(O34-O53)),IF(O34=8,O74/(O38^(O34-O53)),IF(O34=9,O78/(O38^(O34-O53)),IF(O34=10,O82/(O38^(O34-O53)))))))))))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<3) else (((params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']) if (params['kolichestvo_stupenej_drosselirovaniya_j']==3) else (((params['perepad_davlenij_n4']/(params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n3']))) if (params['kolichestvo_stupenej_drosselirovaniya_j']==4) else (((params['perepad_davlenij_n5']/(params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n3']))) if (params['kolichestvo_stupenej_drosselirovaniya_j']==5) else (((params['perepad_davlenij_n6']/(params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n3']))) if (params['kolichestvo_stupenej_drosselirovaniya_j']==6) else (((params['perepad_davlenij_n7']/(params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n3']))) if (params['kolichestvo_stupenej_drosselirovaniya_j']==7) else (((params['perepad_davlenij_n8']/(params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n3']))) if (params['kolichestvo_stupenej_drosselirovaniya_j']==8) else (((params['perepad_davlenij_n9']/(params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n3']))) if (params['kolichestvo_stupenej_drosselirovaniya_j']==9) else (((params['perepad_davlenij_n10']/(params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n3']))) if (params['kolichestvo_stupenej_drosselirovaniya_j']==10) else (None)))))))))))))))))))

def calc_gazodinamicheskaya_funkciya_rashoda_q_n3(params):
    """
    Excel M55 / O55
    Формула (Excel): =IF(O34>2,IF(O54^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O54^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O54^(($O$31-1)/$O$31))),1),"")
    """
    return ((((((params['perepad_davlenij_n3']**(1/params['koeffcient_adiabaty'])/(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1)))*math.sqrt((params['koeffcient_adiabaty']+1)/(params['koeffcient_adiabaty']-1)*(1-params['perepad_davlenij_n3']**((params['koeffcient_adiabaty']-1)/params['koeffcient_adiabaty'])))) if (params['perepad_davlenij_n3']**(1/params['koeffcient_adiabaty'])>(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1))) else (1))) if (params['kolichestvo_stupenej_drosselirovaniya_j']>2) else (None)))

def calc_oblast_n3(params):
    """
    Excel M56 / O56
    Формула (Excel): =IF(O34<3,"",IF(AND(O54<1,O54>O144),"Дозвуковая область","Сверхзвуковая область"))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<3) else ((("Дозвуковая область") if ((params['perepad_davlenij_n3']<1 and params['perepad_davlenij_n3']>params['kriticheskij_perepad_davlenij'])) else ("Сверхзвуковая область")))))

def calc_stupeni_n4(params):
    """
    Excel M57 / O57
    Формула (Excel): =IF($E$17>3,"4","")
    """
    return (((4) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>3) else (None)))

def calc_perepad_davlenij_n4(params):
    """
    Excel M58 / O58
    Формула (Excel): =IF($O$34=4,$O$42,IF($O$34<4,"",IF($O$34=5,O62/$O$38^($O$34-O57),IF($O$34=6,O66/$O$38^($O$34-O57),IF($O$34=7,O70/$O$38^($O$34-O57),IF($O$34=8,O74/$O$38^($O$34-O57),IF($O$34=9,O78/$O$38^($O$34-O57),IF($O$34=10,O82/$O$38^($O$34-O57)))))))))
    """
    return (((params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']) if (params['kolichestvo_stupenej_drosselirovaniya_j']==4) else (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<4) else (((params['perepad_davlenij_n5']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n4'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==5) else (((params['perepad_davlenij_n6']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n4'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==6) else (((params['perepad_davlenij_n7']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n4'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==7) else (((params['perepad_davlenij_n8']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n4'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==8) else (((params['perepad_davlenij_n9']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n4'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==9) else (((params['perepad_davlenij_n10']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n4'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==10) else (None)))))))))))))))))

def calc_gazodinamicheskaya_funkciya_rashoda_q_n4(params):
    """
    Excel M59 / O59
    Формула (Excel): =IF($O$34>3,IF(O58^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O58^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O58^(($O$31-1)/$O$31))),1),"")
    """
    return ((((((params['perepad_davlenij_n4']**(1/params['koeffcient_adiabaty'])/(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1)))*math.sqrt((params['koeffcient_adiabaty']+1)/(params['koeffcient_adiabaty']-1)*(1-params['perepad_davlenij_n4']**((params['koeffcient_adiabaty']-1)/params['koeffcient_adiabaty'])))) if (params['perepad_davlenij_n4']**(1/params['koeffcient_adiabaty'])>(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1))) else (1))) if (params['kolichestvo_stupenej_drosselirovaniya_j']>3) else (None)))

def calc_oblast_n4(params):
    """
    Excel M60 / O60
    Формула (Excel): =IF(E17>3,IF(AND(O58<1,O58>O144),"Дозвуковая область","Сверхзвуковая область"),"")
    """
    return ((((("Дозвуковая область") if ((params['perepad_davlenij_n4']<1 and params['perepad_davlenij_n4']>params['kriticheskij_perepad_davlenij'])) else ("Сверхзвуковая область"))) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>3) else (None)))

def calc_stupeni_n5(params):
    """
    Excel M61 / O61
    Формула (Excel): =IF($E$17>4,5,"")
    """
    return (((5) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>4) else (None)))

def calc_perepad_davlenij_n5(params):
    """
    Excel M62 / O62
    Формула (Excel): =IF($O$34=5,$O$42,IF($O$34<5,"",IF($O$34=6,O66/$O$38^($O$34-O61),IF($O$34=7,O70/$O$38^($O$34-O61),IF($O$34=8,O74/$O$38^($O$34-O61),IF($O$34=9,O78/$O$38^($O$34-O61),IF($O$34=10,O82/$O$38^($O$34-O61))))))))
    """
    return (((params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']) if (params['kolichestvo_stupenej_drosselirovaniya_j']==5) else (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<5) else (((params['perepad_davlenij_n6']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n5'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==6) else (((params['perepad_davlenij_n7']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n5'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==7) else (((params['perepad_davlenij_n8']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n5'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==8) else (((params['perepad_davlenij_n9']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n5'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==9) else (((params['perepad_davlenij_n10']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n5'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==10) else (None)))))))))))))))

def calc_gazodinamicheskaya_funkciya_rashoda_q_n5(params):
    """
    Excel M63 / O63
    Формула (Excel): =IF($O$34>4,IF(O62^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O62^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O62^(($O$31-1)/$O$31))),1),"")
    """
    return ((((((params['perepad_davlenij_n5']**(1/params['koeffcient_adiabaty'])/(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1)))*math.sqrt((params['koeffcient_adiabaty']+1)/(params['koeffcient_adiabaty']-1)*(1-params['perepad_davlenij_n5']**((params['koeffcient_adiabaty']-1)/params['koeffcient_adiabaty'])))) if (params['perepad_davlenij_n5']**(1/params['koeffcient_adiabaty'])>(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1))) else (1))) if (params['kolichestvo_stupenej_drosselirovaniya_j']>4) else (None)))

def calc_oblast_n5(params):
    """
    Excel M64 / O64
    Формула (Excel): =IF($E$17>4,IF(AND(O58<1,O58>$O$144),"Дозвуковая область","Сверхзвуковая область"),"")
    """
    return ((((("Дозвуковая область") if ((params['perepad_davlenij_n4']<1 and params['perepad_davlenij_n4']>params['kriticheskij_perepad_davlenij'])) else ("Сверхзвуковая область"))) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>4) else (None)))

def calc_stupeni_n6(params):
    """
    Excel M65 / O65
    Формула (Excel): =IF($E$17>5,6,"")
    """
    return (((6) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>5) else (None)))

def calc_perepad_davlenij_n6(params):
    """
    Excel M66 / O66
    Формула (Excel): =IF($O$34=6,$O$42,IF($O$34<6,"",IF($O$34=7,O70/$O$38^($O$34-O65),IF($O$34=8,O74/$O$38^($O$34-O65),IF($O$34=9,O78/$O$38^($O$34-O65),IF($O$34=10,O82/$O$38^($O$34-O65)))))))
    """
    return (((params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']) if (params['kolichestvo_stupenej_drosselirovaniya_j']==6) else (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<6) else (((params['perepad_davlenij_n7']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n6'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==7) else (((params['perepad_davlenij_n8']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n6'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==8) else (((params['perepad_davlenij_n9']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n6'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==9) else (((params['perepad_davlenij_n10']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n6'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==10) else (None)))))))))))))

def calc_gazodinamicheskaya_funkciya_rashoda_q_n6(params):
    """
    Excel M67 / O67
    Формула (Excel): =IF($O$34>5,IF(O66^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O66^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O66^(($O$31-1)/$O$31))),1),"")
    """
    return ((((((params['perepad_davlenij_n6']**(1/params['koeffcient_adiabaty'])/(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1)))*math.sqrt((params['koeffcient_adiabaty']+1)/(params['koeffcient_adiabaty']-1)*(1-params['perepad_davlenij_n6']**((params['koeffcient_adiabaty']-1)/params['koeffcient_adiabaty'])))) if (params['perepad_davlenij_n6']**(1/params['koeffcient_adiabaty'])>(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1))) else (1))) if (params['kolichestvo_stupenej_drosselirovaniya_j']>5) else (None)))

def calc_oblast_n6(params):
    """
    Excel M68 / O68
    Формула (Excel): =IF($E$17>5,IF(AND(O62<1,O62>$O$144),"Дозвуковая область","Сверхзвуковая область"),"")
    """
    return ((((("Дозвуковая область") if ((params['perepad_davlenij_n5']<1 and params['perepad_davlenij_n5']>params['kriticheskij_perepad_davlenij'])) else ("Сверхзвуковая область"))) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>5) else (None)))

def calc_stupeni_n7(params):
    """
    Excel M69 / O69
    Формула (Excel): =IF($E$17>6,7,"")
    """
    return (((7) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>6) else (None)))

def calc_perepad_davlenij_n7(params):
    """
    Excel M70 / O70
    Формула (Excel): =IF($O$34=7,$O$42,IF($O$34<7,"",IF($O$34=8,O74/$O$38^($O$34-O69),IF($O$34=9,O78/$O$38^($O$34-O69),IF($O$34=10,O82/$O$38^($O$34-O69))))))
    """
    return (((params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']) if (params['kolichestvo_stupenej_drosselirovaniya_j']==7) else (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<7) else (((params['perepad_davlenij_n8']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n7'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==8) else (((params['perepad_davlenij_n9']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n7'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==9) else (((params['perepad_davlenij_n10']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n7'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==10) else (None)))))))))))


def calc_gazodinamicheskaya_funkciya_rashoda_q_n7(params):
    """
    Excel M71 / O71
    Формула (Excel): =IF($O$34>6,IF(O70^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O70^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O70^(($O$31-1)/$O$31))),1),"")
    """
    return ((((((params['perepad_davlenij_n7']**(1/params['koeffcient_adiabaty'])/(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1)))*math.sqrt((params['koeffcient_adiabaty']+1)/(params['koeffcient_adiabaty']-1)*(1-params['perepad_davlenij_n7']**((params['koeffcient_adiabaty']-1)/params['koeffcient_adiabaty'])))) if (params['perepad_davlenij_n7']**(1/params['koeffcient_adiabaty'])>(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1))) else (1))) if (params['kolichestvo_stupenej_drosselirovaniya_j']>6) else (None)))

def calc_oblast_n7(params):
    """
    Excel M72 / O72
    Формула (Excel): =IF($E$17>6,IF(AND(O66<1,O66>$O$144),"Дозвуковая область","Сверхзвуковая область"),"")
    """
    return ((((("Дозвуковая область") if ((params['perepad_davlenij_n6']<1 and params['perepad_davlenij_n6']>params['kriticheskij_perepad_davlenij'])) else ("Сверхзвуковая область"))) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>6) else (None)))

def calc_stupeni_n8(params):
    """
    Excel M73 / O73
    Формула (Excel): =IF($E$17>7,8,"")
    """
    return (((8) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>7) else (None)))

def calc_perepad_davlenij_n8(params):
    """
    Excel M74 / O74
    Формула (Excel): =IF($O$34=8,$O$42,IF($O$34<8,"",IF($O$34=9,O78/$O$38^($O$34-O73),IF($O$34=10,O82/$O$38^($O$34-O73)))))
    """
    return (((params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']) if
             (params['kolichestvo_stupenej_drosselirovaniya_j']==8) else
             (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<8)
               else (((params['perepad_davlenij_n9']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n8']))
                      if (params['kolichestvo_stupenej_drosselirovaniya_j']==9) else
                      (((params['perepad_davlenij_n10']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n8']))
                        if (params['kolichestvo_stupenej_drosselirovaniya_j']==10) else (None)))))))))

def calc_gazodinamicheskaya_funkciya_rashoda_q_n8(params):
    """
    Excel M75 / O75
    Формула (Excel): =IF($O$34>7,IF(O74^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O74^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O74^(($O$31-1)/$O$31))),1),"")
    """
    return ((((((params['perepad_davlenij_n8']**(1/params['koeffcient_adiabaty'])/(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1)))*math.sqrt((params['koeffcient_adiabaty']+1)/(params['koeffcient_adiabaty']-1)*(1-params['perepad_davlenij_n8']**((params['koeffcient_adiabaty']-1)/params['koeffcient_adiabaty'])))) if (params['perepad_davlenij_n8']**(1/params['koeffcient_adiabaty'])>(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1))) else (1))) if (params['kolichestvo_stupenej_drosselirovaniya_j']>7) else (None)))

def calc_oblast_n8(params):
    """
    Excel M76 / O76
    Формула (Excel): =IF($E$17>7,IF(AND(O70<1,O70>$O$144),"Дозвуковая область","Сверхзвуковая область"),"")
    """
    return ((((("Дозвуковая область") if ((params['perepad_davlenij_n7']<1 and params['perepad_davlenij_n7']>params['kriticheskij_perepad_davlenij'])) else ("Сверхзвуковая область"))) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>7) else (None)))

def calc_stupeni_n9(params):
    """
    Excel M77 / O77
    Формула (Excel): =IF($E$17>8,9,"")
    """
    return (((9) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>8) else (None)))

def calc_perepad_davlenij_n9(params):
    """
    Excel M78 / O78
    Формула (Excel): =IF($O$34=9,$O$42,IF($O$34<9,"",IF($O$34=10,O82/$O$38^($O$34-O77))))
    """
    return (((params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']) if (params['kolichestvo_stupenej_drosselirovaniya_j']==9) else (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<9) else (((params['perepad_davlenij_n10']/params['gradient_skorosti_w']**(params['kolichestvo_stupenej_drosselirovaniya_j']-params['stupeni_n9'])) if (params['kolichestvo_stupenej_drosselirovaniya_j']==10) else (None)))))))

def calc_gazodinamicheskaya_funkciya_rashoda_q_n9(params):
    """
    Excel M79 / O79
    Формула (Excel): =IF($O$34>8,IF(O78^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O78^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O78^(($O$31-1)/$O$31))),1),"")
    """
    return ((((((params['perepad_davlenij_n9']**(1/params['koeffcient_adiabaty'])/(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1)))*math.sqrt((params['koeffcient_adiabaty']+1)/(params['koeffcient_adiabaty']-1)*(1-params['perepad_davlenij_n9']**((params['koeffcient_adiabaty']-1)/params['koeffcient_adiabaty'])))) if (params['perepad_davlenij_n9']**(1/params['koeffcient_adiabaty'])>(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1))) else (1))) if (params['kolichestvo_stupenej_drosselirovaniya_j']>8) else (None)))

def calc_oblast_n9(params):
    """
    Excel M80 / O80
    Формула (Excel): =IF($E$17>8,IF(AND(O74<1,O74>$O$144),"Дозвуковая область","Сверхзвуковая область"),"")
    """
    return ((((("Дозвуковая область") if ((params['perepad_davlenij_n8']<1 and params['perepad_davlenij_n8']>params['kriticheskij_perepad_davlenij'])) else ("Сверхзвуковая область"))) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>8) else (None)))

def calc_stupeni_n10(params):
    """
    Excel M81 / O81
    Формула (Excel): =IF($E$17>9,10,"")
    """
    return (((10) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>9) else (None)))

def calc_perepad_davlenij_n10(params):
    """
    Excel M82 / O82
    Формула (Excel): =IF($O$34=10,$O$42,IF($O$34<10,""))
    """
    return (((params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']) if (params['kolichestvo_stupenej_drosselirovaniya_j']==10) else (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<10) else (None)))))

def calc_gazodinamicheskaya_funkciya_rashoda_q_n10(params):
    """
    Excel M83 / O83
    Формула (Excel): =IF($O$34>9,IF(O82^(1/$O$31)>(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)),(O82^(1/$O$31)/(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))*SQRT(($O$31+1)/($O$31-1)*(1-O82^(($O$31-1)/$O$31))),1),"")
    """
    return ((((((params['perepad_davlenij_n10']**(1/params['koeffcient_adiabaty'])/(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1)))*math.sqrt((params['koeffcient_adiabaty']+1)/(params['koeffcient_adiabaty']-1)*(1-params['perepad_davlenij_n10']**((params['koeffcient_adiabaty']-1)/params['koeffcient_adiabaty'])))) if (params['perepad_davlenij_n10']**(1/params['koeffcient_adiabaty'])>(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1))) else (1))) if (params['kolichestvo_stupenej_drosselirovaniya_j']>9) else (None)))

def calc_oblast_n10(params):
    """
    Excel M84 / O84
    Формула (Excel): =IF($E$17>9,IF(AND(O78<1,O78>$O$144),"Дозвуковая область","Сверхзвуковая область"),"")
    """
    return ((((("Дозвуковая область") if ((params['perepad_davlenij_n9']<1 and params['perepad_davlenij_n9']>params['kriticheskij_perepad_davlenij'])) else ("Сверхзвуковая область"))) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>9) else (None)))

def calc_stupenin1_2_n1(params):
    """
    Excel M90 / O90
    Формула (Excel): 1
    """
    return (1)

def calc_diametry_otverstij_mm_n1(params):
    """
    Excel M91 / O91
    Формула (Excel): =SQRT(4*O92/(0.8*PI()*$O$35))
    """
    return (math.sqrt(4*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n1']/(0.8*math.pi*params['maksimalnoe_kolichestvo_otverstij_kmah_v_drosselnoj_reshetke_sht'])))

def calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n1(params):
    """
    Excel M92 / O92
    Формула (Excel): =($O$31+1)/(2*$O$31)*O24*O28/(O26*O47*(1-(($O$31-1)/($O$31+1)))^(1/($O$31-1)))
    """
    return ((params['koeffcient_adiabaty']+1)/(2*params['koeffcient_adiabaty'])*params['rashod_sredy_g_kg_s']*params['kriticheskaya_skorost_skr_m_s']/(params['davlenie_na_vhode_v_shg_pi_abs_mpa']*params['gazodinamicheskaya_funkciya_rashoda_q_n1']*(1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1)))**(1/(params['koeffcient_adiabaty']-1))))

def calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n1(params):
    """
    Excel M93 / O93
    Формула (Excel): =5*O92/0.8
    """
    return (5*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n1']/0.8)

def calc_stupenin1_2_n2(params):
    """
    Excel M94 / O94
    Формула (Excel): =IF(O34=1,"",2)
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']==1) else (2)))

def calc_diametry_otverstij_mm_n2(params):
    """
    Excel M95 / O95
    Формула (Excel): =IF(O34=1,"",SQRT(4*O96/(0.8*PI()*$O$35)))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']==1) else (math.sqrt(4*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n2']/(0.8*math.pi*params['maksimalnoe_kolichestvo_otverstij_kmah_v_drosselnoj_reshetke_sht'])))))

def calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n2(params):
    """
    Excel M96 / O96
    Формула (Excel): =IF($O$34=1,"",O92*O47*$O$42*$O$38^-$O$34/(($O$42*$O$38^((O94-1)/2-$O$34))^O94*O51))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']==1) else (params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n1']*params['gazodinamicheskaya_funkciya_rashoda_q_n1']*params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']*params['gradient_skorosti_w']**-params['kolichestvo_stupenej_drosselirovaniya_j']/((params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']*params['gradient_skorosti_w']**((params['stupenin1_2_n2']-1)/2-params['kolichestvo_stupenej_drosselirovaniya_j']))**params['stupenin1_2_n2']*params['gazodinamicheskaya_funkciya_rashoda_q_n2']))))

def calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n2(params):
    """
    Excel M97 / O97
    Формула (Excel): =IF(O34=1,"",5*O96/0.8)
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']==1) else (5*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n2']/0.8)))

def calc_stupenin1_2_n3(params):
    """
    Excel M98 / O98
    Формула (Excel): =IF(O34<3,"",3)
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<3) else (3)))

def calc_diametry_otverstij_mm_n3(params):
    """
    Excel M99 / O99
    Формула (Excel): =IF(O34<3,"",SQRT(4*O100/(0.8*PI()*$O$35)))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<3) else (math.sqrt(4*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n3']/(0.8*math.pi*params['maksimalnoe_kolichestvo_otverstij_kmah_v_drosselnoj_reshetke_sht'])))))

def calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n3(params):
    """
    Excel M100 / O100
    Формула (Excel): =IF(O34<3,"",O92*O47*O42*O38^-O34/((O42*O38^((O98-1)/2-O34))^O98*O55))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<3) else (params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n1']*params['gazodinamicheskaya_funkciya_rashoda_q_n1']*params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']*params['gradient_skorosti_w']**-params['kolichestvo_stupenej_drosselirovaniya_j']/((params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']*params['gradient_skorosti_w']**((params['stupenin1_2_n3']-1)/2-params['kolichestvo_stupenej_drosselirovaniya_j']))**params['stupenin1_2_n3']*params['gazodinamicheskaya_funkciya_rashoda_q_n3']))))

def calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n3(params):
    """
    Excel M101 / O101
    Формула (Excel): =IF(O34<3,"",5*O100/0.8)
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<3) else (5*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n3']/0.8)))

def calc_stupenin1_2_n4(params):
    """
    Excel M102 / O102
    Формула (Excel): =IF(O34<4,"",4)
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<4) else (4)))

def calc_diametry_otverstij_mm_n4(params):
    """
    Excel M103 / O103
    Формула (Excel): =IF(O34<4,"",SQRT(4*O104/(0.8*PI()*$O$35)))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<4) else (math.sqrt(4*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n4']/(0.8*math.pi*params['maksimalnoe_kolichestvo_otverstij_kmah_v_drosselnoj_reshetke_sht'])))))

def calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n4(params):
    """
    Excel M104 / O104
    Формула (Excel): =IF(O34<4,"",O92*O47*O42*O38^-O34/((O42*O38^((O102-1)/2-O34))^O102*O59))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<4) else (params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n1']*params['gazodinamicheskaya_funkciya_rashoda_q_n1']*params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']*params['gradient_skorosti_w']**-params['kolichestvo_stupenej_drosselirovaniya_j']/((params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']*params['gradient_skorosti_w']**((params['stupenin1_2_n4']-1)/2-params['kolichestvo_stupenej_drosselirovaniya_j']))**params['stupenin1_2_n4']*params['gazodinamicheskaya_funkciya_rashoda_q_n4']))))

def calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n4(params):
    """
    Excel M105 / O105
    Формула (Excel): =IF(O34<4,"",5*O104/0.8)
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<4) else (5*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n4']/0.8)))

def calc_stupenin1_2_n5(params):
    """
    Excel M106 / O106
    Формула (Excel): =IF($O$34<5,"",5)
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<5) else (5)))

def calc_diametry_otverstij_mm_n5(params):
    """
    Excel M107 / O107
    Формула (Excel): =IF($O$34<5,"",SQRT(4*O108/(0.8*PI()*$O$35)))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<5) else (math.sqrt(4*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n5']/(0.8*math.pi*params['maksimalnoe_kolichestvo_otverstij_kmah_v_drosselnoj_reshetke_sht'])))))

def calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n5(params):
    """
    Excel M108 / O108
    Формула (Excel): =IF(O34<5,"",$O$92*O47*$O$42*$O$38^-$O$34/(($O$42*$O$38^((O106-1)/2-$O$34))^O106*O63))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<5) else (params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n1']*params['gazodinamicheskaya_funkciya_rashoda_q_n1']*params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']*params['gradient_skorosti_w']**-params['kolichestvo_stupenej_drosselirovaniya_j']/((params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']*params['gradient_skorosti_w']**((params['stupenin1_2_n5']-1)/2-params['kolichestvo_stupenej_drosselirovaniya_j']))**params['stupenin1_2_n5']*params['gazodinamicheskaya_funkciya_rashoda_q_n5']))))

def calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n5(params):
    """
    Excel M109 / O109
    Формула (Excel): =IF($O$34<5,"",5*O108/0.8)
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<5) else (5*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n5']/0.8)))

def calc_stupenin1_2_n6(params):
    """
    Excel M110 / O110
    Формула (Excel): =IF($O$34<6,"",6)
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<6) else (6)))

def calc_diametry_otverstij_mm_n6(params):
    """
    Excel M111 / O111
    Формула (Excel): =IF($O$34<6,"",SQRT(4*O112/(0.8*PI()*$O$35)))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<6) else (math.sqrt(4*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n6']/(0.8*math.pi*params['maksimalnoe_kolichestvo_otverstij_kmah_v_drosselnoj_reshetke_sht'])))))

def calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n6(params):
    """
    Excel M112 / O112
    Формула (Excel): =IF(O34<6,"",$O$92*O47*$O$42*$O$38^-$O$34/(($O$42*$O$38^((O110-1)/2-$O$34))^O110*O67))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<6) else (params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n1']*params['gazodinamicheskaya_funkciya_rashoda_q_n1']*params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']*params['gradient_skorosti_w']**-params['kolichestvo_stupenej_drosselirovaniya_j']/((params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']*params['gradient_skorosti_w']**((params['stupenin1_2_n6']-1)/2-params['kolichestvo_stupenej_drosselirovaniya_j']))**params['stupenin1_2_n6']*params['gazodinamicheskaya_funkciya_rashoda_q_n6']))))

def calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n6(params):
    """
    Excel M113 / O113
    Формула (Excel): =IF($O$34<6,"",5*O112/0.8)
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<6) else (5*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n6']/0.8)))

def calc_stupenin1_2_n7(params):
    """
    Excel M114 / O114
    Формула (Excel): =IF($O$34<7,"",7)
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<7) else (7)))

def calc_diametry_otverstij_mm_n7(params):
    """
    Excel M115 / O115
    Формула (Excel): =IF($O$34<7,"",SQRT(4*O116/(0.8*PI()*$O$35)))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<7) else (math.sqrt(4*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n7']/(0.8*math.pi*params['maksimalnoe_kolichestvo_otverstij_kmah_v_drosselnoj_reshetke_sht'])))))

def calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n7(params):
    """
    Excel M116 / O116
    Формула (Excel): =IF(O34<7,"",$O$92*O47*$O$42*$O$38^-$O$34/(($O$42*$O$38^((O114-1)/2-$O$34))^O114*O71))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<7) else (params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n1']*params['gazodinamicheskaya_funkciya_rashoda_q_n1']*params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']*params['gradient_skorosti_w']**-params['kolichestvo_stupenej_drosselirovaniya_j']/((params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']*params['gradient_skorosti_w']**((params['stupenin1_2_n7']-1)/2-params['kolichestvo_stupenej_drosselirovaniya_j']))**params['stupenin1_2_n7']*params['gazodinamicheskaya_funkciya_rashoda_q_n7']))))

def calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n7(params):
    """
    Excel M117 / O117
    Формула (Excel): =IF($O$34<7,"",5*O116/0.8)
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<7) else (5*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n7']/0.8)))

def calc_stupenin1_2_n8(params):
    """
    Excel M118 / O118
    Формула (Excel): =IF($O$34<8,"",8)
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<8) else (8)))

def calc_diametry_otverstij_mm_n8(params):
    """
    Excel M119 / O119
    Формула (Excel): =IF($O$34<8,"",SQRT(4*O120/(0.8*PI()*$O$35)))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<8) else (math.sqrt(4*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n8']/(0.8*math.pi*params['maksimalnoe_kolichestvo_otverstij_kmah_v_drosselnoj_reshetke_sht'])))))

def calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n8(params):
    """
    Excel M120 / O120
    Формула (Excel): =IF(O34<8,"",$O$92*O47*$O$42*$O$38^-$O$34/(($O$42*$O$38^((O118-1)/2-$O$34))^O118*O75))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<8) else (params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n1']*params['gazodinamicheskaya_funkciya_rashoda_q_n1']*params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']*params['gradient_skorosti_w']**-params['kolichestvo_stupenej_drosselirovaniya_j']/((params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']*params['gradient_skorosti_w']**((params['stupenin1_2_n8']-1)/2-params['kolichestvo_stupenej_drosselirovaniya_j']))**params['stupenin1_2_n8']*params['gazodinamicheskaya_funkciya_rashoda_q_n8']))))

def calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n8(params):
    """
    Excel M121 / O121
    Формула (Excel): =IF($O$34<8,"",5*O120/0.8)
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<8) else (5*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n8']/0.8)))

def calc_stupenin1_2_n9(params):
    """
    Excel M122 / O122
    Формула (Excel): =IF($O$34<9,"",9)
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<9) else (9)))

def calc_diametry_otverstij_mm_n9(params):
    """
    Excel M123 / O123
    Формула (Excel): =IF($O$34<9,"",SQRT(4*O124/(0.8*PI()*$O$35)))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<9) else (math.sqrt(4*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n9']/(0.8*math.pi*params['maksimalnoe_kolichestvo_otverstij_kmah_v_drosselnoj_reshetke_sht'])))))

def calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n9(params):
    """
    Excel M124 / O124
    Формула (Excel): =IF(O34<9,"",$O$92*O47*$O$42*$O$38^-$O$34/(($O$42*$O$38^((O122-1)/2-$O$34))^O122*O79))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<9) else (params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n1']*params['gazodinamicheskaya_funkciya_rashoda_q_n1']*params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']*params['gradient_skorosti_w']**-params['kolichestvo_stupenej_drosselirovaniya_j']/((params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']*params['gradient_skorosti_w']**((params['stupenin1_2_n9']-1)/2-params['kolichestvo_stupenej_drosselirovaniya_j']))**params['stupenin1_2_n9']*params['gazodinamicheskaya_funkciya_rashoda_q_n9']))))

def calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n9(params):
    """
    Excel M125 / O125
    Формула (Excel): =IF($O$34<9,"",5*O124/0.8)
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<9) else (5*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n9']/0.8)))

def calc_stupenin1_2_n10(params):
    """
    Excel M126 / O126
    Формула (Excel): =IF($O$34<10,"",10)
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<10) else (10)))

def calc_diametry_otverstij_mm_n10(params):
    """
    Excel M127 / O127
    Формула (Excel): =IF($O$34<10,"",SQRT(4*O128/(0.8*PI()*$O$35)))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<10) else (math.sqrt(4*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n10']/(0.8*math.pi*params['maksimalnoe_kolichestvo_otverstij_kmah_v_drosselnoj_reshetke_sht'])))))

def calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n10(params):
    """
    Excel M128 / O128
    Формула (Excel): =IF(O34<10,"",$O$92*O47*$O$42*$O$38^-$O$34/(($O$42*$O$38^((O126-1)/2-$O$34))^O126*O83))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<10) else (params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n1']*params['gazodinamicheskaya_funkciya_rashoda_q_n1']*params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']*params['gradient_skorosti_w']**-params['kolichestvo_stupenej_drosselirovaniya_j']/((params['otnositelnyj_perepad_davleniya_na_poslednej_reshetke']*params['gradient_skorosti_w']**((params['stupenin1_2_n10']-1)/2-params['kolichestvo_stupenej_drosselirovaniya_j']))**params['stupenin1_2_n10']*params['gazodinamicheskaya_funkciya_rashoda_q_n10']))))

def calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n10(params):
    """
    Excel M129 / O129
    Формула (Excel): =IF($O$34<10,"",5*O128/0.8)
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<10) else (5*params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n10']/0.8)))

def calc_temperatura_k(params):
    """
    Excel M135 / O135
    Формула (Excel): =O25+273.15
    """
    return (params['temperatura_sredy_s_2']+params.get('zero_celsius_k', 273.15))

def calc_sa_ploschad_secheniya_shumoglushitelya_m2(params):
    """
    Excel M136 / O136
    Формула (Excel): =PI()*O139^2/4
    """
    return (math.pi*params['da_vnutrennij_diametr_vyhlopa_iz_korpusa_m']**2/4)

def calc_perimetr_m(params):
    """
    Excel M137 / O137
    Формула (Excel): =PI()*E27
    """
    return (math.pi*params['vnutrennij_diametr_shumoglushitelya_korpus_m'])

def calc_sk_ploschad_vyhodnogo_secheniya_korpusa_do_kryshki_kv_m(params):
    """
    Excel M138 / O138
    Формула (Excel): =PI()*E27*E35
    """
    return (math.pi*params['vnutrennij_diametr_shumoglushitelya_korpus_m']*params['rasstoyanie_ot_korpusa_do_kryshki_m'])

def calc_da_vnutrennij_diametr_vyhlopa_iz_korpusa_m(params):
    """
    Excel M139 / O139
    Формула (Excel): =E27-2*E28
    """
    return (params['vnutrennij_diametr_shumoglushitelya_korpus_m']-2*params['tolschina_oblicovki_m'])

def calc_nezapolnennaya_ploschad_kv_m(params):
    """
    Excel M140 / O140
    Формула (Excel): =O136-E33
    """
    return (params['sa_ploschad_secheniya_shumoglushitelya_m2']-params['ploschadi_zanyatye_plastinami_shumoglusheniya_m2'])


def calc_gidravlicheskij_diametr_m(params):
    """
    Excel M141 / O141
    Формула (Excel): =4*O140/E34
    """
    return (4*params['nezapolnennaya_ploschad_kv_m']/params['perimetr_svobodnogo_secheniya_m'])

def calc_otnositelnaya_ploschad(params):
    """
    Excel M142 / O142
    Формула (Excel): =O140/O136
    """
    return (params['nezapolnennaya_ploschad_kv_m']/params['sa_ploschad_secheniya_shumoglushitelya_m2'])


def calc_pd_srednij_skorostnoj_napor_na_vyhode_iz_schelevyh_kanalov(params):
    """
    Расчет среднего скоростного напора на выходе из щелевых каналов.

    Excel M143 / O143
    Формула: =MAX(O318,O333,O348,O363,O378,O393)
    """
    pressures = [
        params.get('pd_skorostnoj_napor_na_vyhode_pa_n1'),
        params.get('pd_skorostnoj_napor_na_vyhode_pa_n2'),
        params.get('pd_skorostnoj_napor_na_vyhode_pa_n3'),
        params.get('pd_skorostnoj_napor_na_vyhode_pa_n4'),
        params.get('pd_skorostnoj_napor_na_vyhode_pa_n5'),
        params.get('pd_skorostnoj_napor_na_vyhode_pa_n6')
    ]

    # Фильтруем None значения
    valid_pressures = [p for p in pressures if p is not None]

    # Если есть валидные значения, возвращаем максимум, иначе 0
    return max(valid_pressures) if valid_pressures else 0


def calc_kriticheskij_perepad_davlenij(params):
    """
    Excel M144 / O144
    Формула (Excel): =(2/($O$31+1))^($O$31/($O$31-1))
    """
    return ((2/(params['koeffcient_adiabaty']+1))**(params['koeffcient_adiabaty']/(params['koeffcient_adiabaty']-1)))

def calc_pk_izbytochnoe_davlenie_pod_kryshkoj_pa(params):
    """
    Excel M150 / O150
    Формула (Excel): =O284
    """
    return (params['pk_izbytochnoe_davlenie_pod_kryshkoj_pa_2'])

def calc_pa_izbytochnoe_davlenie_na_vyhode_iz_korpusa_za_stupenyu_zvukopogloscheniya_pa(params):
    """
    Excel M151 / O151
    Формула (Excel): =O285
    """
    return (params['pa_izbytochnoe_davlenie_na_vyhode_iz_korpusa_za_stupenyu_zvukopogloscheniya_pa_2'])

def calc_pa_absolyutnoe_davlenie_za_stupenyu_zvukopogloscheniya_pa(params):
    """
    Excel M152 / O152
    Формула (Excel): =O286
    """
    return (params['pa_absolyutnoe_davlenie_za_stupenyu_zvukopogloscheniya_pa_2'])

def calc_pi3_davlenie_pered_stupenyu_zvukopogloscheniya_pa(params):
    """
    Excel M153 / O153
    Формула (Excel): =O267
    """
    return (params['pi3_davlenie_pered_stupenyu_zvukopogloscheniya_pa_2'])

def calc_izbytochnoe_davlenie_pod_kryshkoj_ne_mozhet_prevyshat_15000_pa(params):
    """
    Excel M154 / O154
    Формула (Excel): =IF(O150>=0.15*10^5,"ОШИБКА","")
    """
    return ((("ОШИБКА") if (params['pk_izbytochnoe_davlenie_pod_kryshkoj_pa']>=0.15*10**5) else (None)))

def calc_izbytochnoe_davlenie_na_vyhode_iz_korpusa_za_stupenyu_zvukopogloscheniya_ne_mozhet_prevyshat_15000_pa(params):
    """
    Excel M155 / O155
    Формула (Excel): =IF(O151>=0.15*10^5,"ОШИБКА","")
    """
    return ((("ОШИБКА") if (params['pa_izbytochnoe_davlenie_na_vyhode_iz_korpusa_za_stupenyu_zvukopogloscheniya_pa']>=0.15*10**5) else (None)))

def calc_wa_skorost_na_vyhode_iz_korpusa_m_s(params):
    """
    Excel M161 / O161
    Формула (Excel): =O291
    """
    return (params['wa_skorost_na_vyhode_iz_korpusa_m_s_2'])

def calc_wk_skorost_na_vyhlope_v_atmosferu_m_s(params):
    """
    Excel M162 / O162
    Формула (Excel): =O292
    """
    return (params['wk_skorost_na_vyhlope_v_atmosferu_m_s_2'])

def calc_ma_chislo_maha_na_vyhode_iz_korpusa(params):
    """
    Excel M163 / O163
    Формула (Excel): =O293
    """
    return (params['ma_chislo_maha_na_vyhode_iz_korpusa_2'])

def calc_mk_chislo_maha_na_vyhlope_v_atmosferu(params):
    """
    Excel M164 / O164
    Формула (Excel): =O294
    """
    return (params['mk_chislo_maha_na_vyhlope_v_atmosferu_2'])

def calc_dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_bokovom_vyhlope_kn(params):
    """
    Excel M168 / O168
    Формула (Excel): =O306
    """
    return (params['dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_bokovom_vyhlope_kn_2'])

def calc_dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_osevom_vyhlope_kn(params):
    """
    Excel M169 / O169
    Формула (Excel): =O307
    """
    return (params['dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_osevom_vyhlope_kn_2'])

def calc_dinamicheskaya_nagruzka_na_drosselnyj_blok_kn(params):
    """
    Excel M170 / O170
    Формула (Excel): =O304
    """
    return (params['dinamicheskaya_nagruzka_na_drosselnyj_blok_kn_2'])

def calc_dinamicheskaya_nagruzka_na_stupen_zvukopogloscheniya_kn(params):
    """
    Excel M171 / O171
    Формула (Excel): =O305
    """
    return (params['dinamicheskaya_nagruzka_na_stupen_zvukopogloscheniya_kn_2'])

def calc_davlenie_za_reshetkami_mpa_n0(params):
    """
    Excel M174 / O174
    Формула (Excel): =O181/O183
    """
    return (params['davlenie_za_reshetkami_mpa_n1']/params['perepad_davlenij_n1_2'])

def calc_stupeni_n1_3(params):
    """
    Excel M180 / O180
    Формула (Excel): 1
    """
    return (1)

def calc_davlenie_za_reshetkami_mpa_n1(params):
    """
    Excel M181 / O181
    Формула (Excel): =IF(E17=1,O27,O188/O190)
    """
    return (((params['davlenie_na_vyhode_iz_shg_pe_mpa']) if (params['kolichestvo_stupenej_drosselirovaniya_sht']==1) else (params['davlenie_za_reshetkami_mpa_n2']/params['perepad_davlenij_n2_2'])))

def calc_y_n1(params):
    """
    Excel M182 / O182
    Формула (Excel): =O13/(O92*O181)
    """
    return (params['k']/(params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n1']*params['davlenie_za_reshetkami_mpa_n1']))

def calc_perepad_davlenij_n1_2(params):
    """
    Excel M183 / O183
    Формула (Excel): =IF(O182>=O14,1/O182,O185*O186)
    """
    return (((1/params['y_n1']) if (params['y_n1']>=params['y_1']) else (params['n1_2']*params['n1_3'])))

def calc_n1(params):
    """
    Excel M184 / O184
    Формула (Excel): =(-1+(1+4*(($O$31-1)/($O$31+1))*O12^2*O182^2)^0.5)/(2*(($O$31-1)/($O$31+1))*O12*O182)
    """
    return ((-1+(1+4*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']**2*params['y_n1']**2)**0.5)/(2*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']*params['y_n1']))

def calc_n1_2(params):
    """
    Excel M185 / O185
    Формула (Excel): =(1-(($O$31-1)/($O$31+1))*O184^2)^(1/($O$31-1))
    """
    return ((1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n1']**2)**(1/(params['koeffcient_adiabaty']-1)))

def calc_n1_3(params):
    """
    Excel M186 / O186
    Формула (Excel): =1-(($O$31-1)/($O$31+1))*O184^2
    """
    return (1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n1']**2)

def calc_stupeni_n2_3(params):
    """
    Excel M187 / O187
    Формула (Excel): =IF($O$34>1,2,"")
    """
    return (((2) if (params['kolichestvo_stupenej_drosselirovaniya_j']>1) else (None)))

def calc_davlenie_za_reshetkami_mpa_n2(params):
    """
    Excel M188 / O188
    Формула (Excel): =IF(O187="","",IF(E17=2,O27,O195/O197))
    """
    return (((None) if (params['stupeni_n2_3']==None) else (((params['davlenie_na_vyhode_iz_shg_pe_mpa']) if (params['kolichestvo_stupenej_drosselirovaniya_sht']==2) else (params['davlenie_za_reshetkami_mpa_n3']/params['perepad_davlenij_n3_2'])))))

def calc_y_n2(params):
    """
    Excel M189 / O189
    Формула (Excel): =IF(O187="","",O13/(O96*O188))
    """
    return (((None) if (params['stupeni_n2_3']==None) else (params['k']/(params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n2']*params['davlenie_za_reshetkami_mpa_n2']))))

def calc_perepad_davlenij_n2_2(params):
    """
    Excel M190 / O190
    Формула (Excel): =IF(O187="","",IF(O189>=O14,1/O189,O192*O193))
    """
    return (((None) if (params['stupeni_n2_3']==None) else (((1/params['y_n2']) if (params['y_n2']>=params['y_1']) else (params['n2_2']*params['n2_3'])))))

def calc_n2(params):
    """
    Excel M191 / O191
    Формула (Excel): =IF(O187="","",(-1+(1+4*(($O$31-1)/($O$31+1))*O12^2*O189^2)^0.5)/(2*(($O$31-1)/($O$31+1))*O12*O189))
    """
    return (((None) if (params['stupeni_n2_3']==None) else ((-1+(1+4*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']**2*params['y_n2']**2)**0.5)/(2*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']*params['y_n2']))))

def calc_n2_2(params):
    """
    Excel M192 / O192
    Формула (Excel): =IF(O187="","",(1-(($O$31-1)/($O$31+1))*O191^2)^(1/($O$31-1)))
    """
    return (((None) if (params['stupeni_n2_3']==None) else ((1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n2']**2)**(1/(params['koeffcient_adiabaty']-1)))))

def calc_n2_3(params):
    """
    Excel M193 / O193
    Формула (Excel): =IF(O187="","",1-(($O$31-1)/($O$31+1))*O191^2)
    """
    return (((None) if (params['stupeni_n2_3']==None) else (1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n2']**2)))

def calc_stupeni_n3_3(params):
    """
    Excel M194 / O194
    Формула (Excel): =IF($O$34>2,3,"")
    """
    return (((3) if (params['kolichestvo_stupenej_drosselirovaniya_j']>2) else (None)))

def calc_davlenie_za_reshetkami_mpa_n3(params):
    """
    Excel M195 / O195
    Формула (Excel): =IF(O194="","",IF(E17=3,O27,O202/O204))
    """
    return (((None) if (params['stupeni_n3_3']==None) else (((params['davlenie_na_vyhode_iz_shg_pe_mpa']) if (params['kolichestvo_stupenej_drosselirovaniya_sht']==3) else (params['davlenie_za_reshetkami_mpa_n4']/params['perepad_davlenij_n4_2'])))))

def calc_y_n3(params):
    """
    Excel M196 / O196
    Формула (Excel): =IF(O194="","",O13/(O100*O195))
    """
    return (((None) if (params['stupeni_n3_3']==None) else (params['k']/(params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n3']*params['davlenie_za_reshetkami_mpa_n3']))))

def calc_perepad_davlenij_n3_2(params):
    """
    Excel M197 / O197
    Формула (Excel): =IF(O194="","",IF(O196>=O14,1/O196,O199*O200))
    """
    return (((None) if (params['stupeni_n3_3']==None) else (((1/params['y_n3']) if (params['y_n3']>=params['y_1']) else (params['n3_2']*params['n3_3'])))))

def calc_n3(params):
    """
    Excel M198 / O198
    Формула (Excel): =IF(O194="","",(-1+(1+4*(($O$31-1)/($O$31+1))*O12^2*O196^2)^0.5)/(2*(($O$31-1)/($O$31+1))*O12*O196))
    """
    return (((None) if (params['stupeni_n3_3']==None) else ((-1+(1+4*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']**2*params['y_n3']**2)**0.5)/(2*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']*params['y_n3']))))

def calc_n3_2(params):
    """
    Excel M199 / O199
    Формула (Excel): =IF(O194="","",(1-(($O$31-1)/($O$31+1))*O198^2)^(1/($O$31-1)))
    """
    return (((None) if (params['stupeni_n3_3']==None) else ((1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n3']**2)**(1/(params['koeffcient_adiabaty']-1)))))

def calc_n3_3(params):
    """
    Excel M200 / O200
    Формула (Excel): =IF(O194="","",1-(($O$31-1)/($O$31+1))*O198^2)
    """
    return (((None) if (params['stupeni_n3_3']==None) else (1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n3']**2)))

def calc_stupeni_n4_3(params):
    """
    Excel M201 / O201
    Формула (Excel): =IF($E$17>3,4,"")
    """
    return (((4) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>3) else (None)))

def calc_davlenie_za_reshetkami_mpa_n4(params):
    """
    Excel M202 / O202
    Формула (Excel): =IF(O201="","",IF($E$17=4,$O$27,O209/O211))
    """
    return (((None) if (params['stupeni_n4_3']==None) else (((params['davlenie_na_vyhode_iz_shg_pe_mpa']) if (params['kolichestvo_stupenej_drosselirovaniya_sht']==4) else (params['davlenie_za_reshetkami_mpa_n5']/params['perepad_davlenij_n5_2'])))))

def calc_y_n4(params):
    """
    Excel M203 / O203
    Формула (Excel): =IF(O201="","",O13/(O104*O202))
    """
    return (((None) if (params['stupeni_n4_3']==None) else (params['k']/(params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n4']*params['davlenie_za_reshetkami_mpa_n4']))))

def calc_perepad_davlenij_n4_2(params):
    """
    Excel M204 / O204
    Формула (Excel): =IF(O201="","",IF(O203>=O14,1/O203,O206*O207))
    """
    return (((None) if (params['stupeni_n4_3']==None) else (((1/params['y_n4']) if (params['y_n4']>=params['y_1']) else (params['n4_2']*params['n4_3'])))))

def calc_n4(params):
    """
    Excel M205 / O205
    Формула (Excel): =IF(O201="","",(-1+(1+4*(($O$31-1)/($O$31+1))*O12^2*O203^2)^0.5)/(2*(($O$31-1)/($O$31+1))*O12*O203))
    """
    return (((None) if (params['stupeni_n4_3']==None) else ((-1+(1+4*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']**2*params['y_n4']**2)**0.5)/(2*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']*params['y_n4']))))

def calc_n4_2(params):
    """
    Excel M206 / O206
    Формула (Excel): =IF(O201="","",(1-(($O$31-1)/($O$31+1))*O205^2)^(1/($O$31-1)))
    """
    return (((None) if (params['stupeni_n4_3']==None) else ((1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n4']**2)**(1/(params['koeffcient_adiabaty']-1)))))

def calc_n4_3(params):
    """
    Excel M207 / O207
    Формула (Excel): =IF(O201="","",1-(($O$31-1)/($O$31+1))*O205^2)
    """
    return (((None) if (params['stupeni_n4_3']==None) else (1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n4']**2)))

def calc_stupeni_n5_3(params):
    """
    Excel M208 / O208
    Формула (Excel): =IF($E$17>4,5,"")
    """
    return (((5) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>4) else (None)))

def calc_davlenie_za_reshetkami_mpa_n5(params):
    """
    Excel M209 / O209
    Формула (Excel): =IF(O208="","",IF($E$17=5,$O$27,O216/O218))
    """
    return (((None) if (params['stupeni_n5_3']==None) else (((params['davlenie_na_vyhode_iz_shg_pe_mpa']) if (params['kolichestvo_stupenej_drosselirovaniya_sht']==5) else (params['davlenie_za_reshetkami_mpa_n6']/params['perepad_davlenij_n6_2'])))))

def calc_y_n5(params):
    """
    Excel M210 / O210
    Формула (Excel): =IF(O208="","",$O$13/(O108*O209))
    """
    return (((None) if (params['stupeni_n5_3']==None) else (params['k']/(params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n5']*params['davlenie_za_reshetkami_mpa_n5']))))

def calc_perepad_davlenij_n5_2(params):
    """
    Excel M211 / O211
    Формула (Excel): =IF(O208="","",IF(O210>=$O$14,1/O210,O213*O214))
    """
    return (((None) if (params['stupeni_n5_3']==None) else (((1/params['y_n5']) if (params['y_n5']>=params['y_1']) else (params['n5_2']*params['n5_3'])))))

def calc_n5(params):
    """
    Excel M212 / O212
    Формула (Excel): =IF(O208="","",(-1+(1+4*(($O$31-1)/($O$31+1))*$O$12^2*O210^2)^0.5)/(2*(($O$31-1)/($O$31+1))*$O$12*O210))
    """
    return (((None) if (params['stupeni_n5_3']==None) else ((-1+(1+4*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']**2*params['y_n5']**2)**0.5)/(2*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']*params['y_n5']))))

def calc_n5_2(params):
    """
    Excel M213 / O213
    Формула (Excel): =IF(O208="","",(1-(($O$31-1)/($O$31+1))*O212^2)^(1/($O$31-1)))
    """
    return (((None) if (params['stupeni_n5_3']==None) else ((1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n5']**2)**(1/(params['koeffcient_adiabaty']-1)))))

def calc_n5_3(params):
    """
    Excel M214 / O214
    Формула (Excel): =IF(O208="","",1-(($O$31-1)/($O$31+1))*O212^2)
    """
    return (((None) if (params['stupeni_n5_3']==None) else (1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n5']**2)))

def calc_stupeni_n6_3(params):
    """
    Excel M215 / O215
    Формула (Excel): =IF($E$17>5,6,"")
    """
    return (((6) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>5) else (None)))

def calc_davlenie_za_reshetkami_mpa_n6(params):
    """
    Excel M216 / O216
    Формула (Excel): =IF(O215="","",IF($E$17=6,$O$27,O223/O225))
    """
    return (((None) if (params['stupeni_n6_3']==None) else (((params['davlenie_na_vyhode_iz_shg_pe_mpa']) if (params['kolichestvo_stupenej_drosselirovaniya_sht']==6) else (params['davlenie_za_reshetkami_mpa_n7']/params['perepad_davlenij_n7_2'])))))

def calc_y_n6(params):
    """
    Excel M217 / O217
    Формула (Excel): =IF(O215="","",$O$13/(O112*O216))
    """
    return (((None) if (params['stupeni_n6_3']==None) else (params['k']/(params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n6']*params['davlenie_za_reshetkami_mpa_n6']))))

def calc_perepad_davlenij_n6_2(params):
    """
    Excel M218 / O218
    Формула (Excel): =IF(O215="","",IF(O217>=$O$14,1/O217,O220*O221))
    """
    return (((None) if (params['stupeni_n6_3']==None) else (((1/params['y_n6']) if (params['y_n6']>=params['y_1']) else (params['n6_2']*params['n6_3'])))))

def calc_n6(params):
    """
    Excel M219 / O219
    Формула (Excel): =IF(O215="","",(-1+(1+4*(($O$31-1)/($O$31+1))*$O$12^2*O217^2)^0.5)/(2*(($O$31-1)/($O$31+1))*$O$12*O217))
    """
    return (((None) if (params['stupeni_n6_3']==None) else ((-1+(1+4*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']**2*params['y_n6']**2)**0.5)/(2*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']*params['y_n6']))))

def calc_n6_2(params):
    """
    Excel M220 / O220
    Формула (Excel): =IF(O215="","",(1-(($O$31-1)/($O$31+1))*O219^2)^(1/($O$31-1)))
    """
    return (((None) if (params['stupeni_n6_3']==None) else ((1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n6']**2)**(1/(params['koeffcient_adiabaty']-1)))))

def calc_n6_3(params):
    """
    Excel M221 / O221
    Формула (Excel): =IF(O215="","",1-(($O$31-1)/($O$31+1))*O219^2)
    """
    return (((None) if (params['stupeni_n6_3']==None) else (1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n6']**2)))

def calc_stupeni_n7_3(params):
    """
    Excel M222 / O222
    Формула (Excel): =IF($E$17>6,7,"")
    """
    return (((7) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>6) else (None)))

def calc_davlenie_za_reshetkami_mpa_n7(params):
    """
    Excel M223 / O223
    Формула (Excel): =IF(O222="","",IF($E$17=7,$O$27,O230/O232))
    """
    return (((None) if (params['stupeni_n7_3']==None) else (((params['davlenie_na_vyhode_iz_shg_pe_mpa']) if (params['kolichestvo_stupenej_drosselirovaniya_sht']==7) else (params['davlenie_za_reshetkami_mpa_n8']/params['perepad_davlenij_n8_2'])))))

def calc_y_n7(params):
    """
    Excel M224 / O224
    Формула (Excel): =IF(O222="","",$O$13/(O116*O223))
    """
    return (((None) if (params['stupeni_n7_3']==None) else (params['k']/(params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n7']*params['davlenie_za_reshetkami_mpa_n7']))))

def calc_perepad_davlenij_n7_2(params):
    """
    Excel M225 / O225
    Формула (Excel): =IF(O222="","",IF(O224>=$O$14,1/O224,O227*O228))
    """
    return (((None) if (params['stupeni_n7_3']==None) else (((1/params['y_n7']) if (params['y_n7']>=params['y_1']) else (params['n7_2']*params['n7_3'])))))

def calc_n7(params):
    """
    Excel M226 / O226
    Формула (Excel): =IF(O222="","",(-1+(1+4*(($O$31-1)/($O$31+1))*$O$12^2*O224^2)^0.5)/(2*(($O$31-1)/($O$31+1))*$O$12*O224))
    """
    return (((None) if (params['stupeni_n7_3']==None) else ((-1+(1+4*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']**2*params['y_n7']**2)**0.5)/(2*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']*params['y_n7']))))

def calc_n7_2(params):
    """
    Excel M227 / O227
    Формула (Excel): =IF(O222="","",(1-(($O$31-1)/($O$31+1))*O226^2)^(1/($O$31-1)))
    """
    return (((None) if (params['stupeni_n7_3']==None) else ((1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n7']**2)**(1/(params['koeffcient_adiabaty']-1)))))

def calc_n7_3(params):
    """
    Excel M228 / O228
    Формула (Excel): =IF(O222="","",1-(($O$31-1)/($O$31+1))*O226^2)
    """
    return (((None) if (params['stupeni_n7_3']==None) else (1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n7']**2)))

def calc_stupeni_n8_3(params):
    """
    Excel M229 / O229
    Формула (Excel): =IF($E$17>7,8,"")
    """
    return (((8) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>7) else (None)))

def calc_davlenie_za_reshetkami_mpa_n8(params):
    """
    Excel M230 / O230
    Формула (Excel): =IF(O229="","",IF($E$17=8,$O$27,O237/O239))
    """
    return (((None) if (params['stupeni_n8_3']==None) else (((params['davlenie_na_vyhode_iz_shg_pe_mpa']) if (params['kolichestvo_stupenej_drosselirovaniya_sht']==8) else (params['davlenie_za_reshetkami_mpa_n9']/params['perepad_davlenij_n9_2'])))))

def calc_y_n8(params):
    """
    Excel M231 / O231
    Формула (Excel): =IF(O229="","",$O$13/(O120*O230))
    """
    return (((None) if (params['stupeni_n8_3']==None) else (params['k']/(params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n8']*params['davlenie_za_reshetkami_mpa_n8']))))

def calc_perepad_davlenij_n8_2(params):
    """
    Excel M232 / O232
    Формула (Excel): =IF(O229="","",IF(O231>=$O$14,1/O231,O234*O235))
    """
    return (((None) if (params['stupeni_n8_3']==None) else (((1/params['y_n8']) if (params['y_n8']>=params['y_1']) else (params['n8_2']*params['n8_3'])))))

def calc_n8(params):
    """
    Excel M233 / O233
    Формула (Excel): =IF(O229="","",(-1+(1+4*(($O$31-1)/($O$31+1))*$O$12^2*O231^2)^0.5)/(2*(($O$31-1)/($O$31+1))*$O$12*O231))
    """
    return (((None) if (params['stupeni_n8_3']==None) else ((-1+(1+4*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']**2*params['y_n8']**2)**0.5)/(2*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']*params['y_n8']))))

def calc_n8_2(params):
    """
    Excel M234 / O234
    Формула (Excel): =IF(O229="","",(1-(($O$31-1)/($O$31+1))*O233^2)^(1/($O$31-1)))
    """
    return (((None) if (params['stupeni_n8_3']==None) else ((1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n8']**2)**(1/(params['koeffcient_adiabaty']-1)))))

def calc_n8_3(params):
    """
    Excel M235 / O235
    Формула (Excel): =IF(O229="","",1-(($O$31-1)/($O$31+1))*O233^2)
    """
    return (((None) if (params['stupeni_n8_3']==None) else (1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n8']**2)))

def calc_stupeni_n9_3(params):
    """
    Excel M236 / O236
    Формула (Excel): =IF($E$17>8,9,"")
    """
    return (((9) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>8) else (None)))

def calc_davlenie_za_reshetkami_mpa_n9(params):
    """
    Excel M237 / O237
    Формула (Excel): =IF(O236="","",IF($E$17=9,$O$27,O244/O246))
    """
    return (((None) if (params['stupeni_n9_3']==None) else (((params['davlenie_na_vyhode_iz_shg_pe_mpa']) if (params['kolichestvo_stupenej_drosselirovaniya_sht']==9) else (params['davlenie_za_reshetkami_mpa_n10']/params['perepad_davlenij_n10_2'])))))

def calc_y_n9(params):
    """
    Excel M238 / O238
    Формула (Excel): =IF(O236="","",$O$13/(O124*O237))
    """
    return (((None) if (params['stupeni_n9_3']==None) else (params['k']/(params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n9']*params['davlenie_za_reshetkami_mpa_n9']))))

def calc_perepad_davlenij_n9_2(params):
    """
    Excel M239 / O239
    Формула (Excel): =IF(O236="","",IF(O238>=$O$14,1/O238,O241*O242))
    """
    return (((None) if (params['stupeni_n9_3']==None) else (((1/params['y_n9']) if (params['y_n9']>=params['y_1']) else (params['n9_2']*params['n9_3'])))))

def calc_n9(params):
    """
    Excel M240 / O240
    Формула (Excel): =IF(O236="","",(-1+(1+4*(($O$31-1)/($O$31+1))*$O$12^2*O238^2)^0.5)/(2*(($O$31-1)/($O$31+1))*$O$12*O238))
    """
    return (((None) if (params['stupeni_n9_3']==None) else ((-1+(1+4*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']**2*params['y_n9']**2)**0.5)/(2*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']*params['y_n9']))))

def calc_n9_2(params):
    """
    Excel M241 / O241
    Формула (Excel): =IF(O236="","",(1-(($O$31-1)/($O$31+1))*O240^2)^(1/($O$31-1)))
    """
    return (((None) if (params['stupeni_n9_3']==None) else ((1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n9']**2)**(1/(params['koeffcient_adiabaty']-1)))))

def calc_n9_3(params):
    """
    Excel M242 / O242
    Формула (Excel): =IF(O236="","",1-(($O$31-1)/($O$31+1))*O240^2)
    """
    return (((None) if (params['stupeni_n9_3']==None) else (1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n9']**2)))

def calc_stupeni_n10_3(params):
    """
    Excel M243 / O243
    Формула (Excel): =IF($E$17>9,10,"")
    """
    return (((10) if (params['kolichestvo_stupenej_drosselirovaniya_sht']>9) else (None)))

def calc_davlenie_za_reshetkami_mpa_n10(params):
    """
    Excel M244 / O244
    Формула (Excel): =IF($O$34<10,"",IF($E$17=10,$O$27))
    """
    return (((None) if (params['kolichestvo_stupenej_drosselirovaniya_j']<10) else (((params['davlenie_na_vyhode_iz_shg_pe_mpa']) if (params['kolichestvo_stupenej_drosselirovaniya_sht']==10) else (None)))))

def calc_y_n10(params):
    """
    Excel M245 / O245
    Формула (Excel): =IF(O243="","",$O$13/(O128*O244))
    """
    return (((None) if (params['stupeni_n10_3']==None) else (params['k']/(params['prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n10']*params['davlenie_za_reshetkami_mpa_n10']))))

def calc_perepad_davlenij_n10_2(params):
    """
    Excel M246 / O246
    Формула (Excel): =IF(O243="","",IF(O245>=$O$14,1/O245,O248*O249))
    """
    return (((None) if (params['stupeni_n10_3']==None) else (((1/params['y_n10']) if (params['y_n10']>=params['y_1']) else (params['n10_2']*params['n10_3'])))))

def calc_n10(params):
    """
    Excel M247 / O247
    Формула (Excel): =IF(O243="","",(-1+(1+4*(($O$31-1)/($O$31+1))*$O$12^2*O245^2)^0.5)/(2*(($O$31-1)/($O$31+1))*$O$12*O245))
    """
    return (((None) if (params['stupeni_n10_3']==None) else ((-1+(1+4*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']**2*params['y_n10']**2)**0.5)/(2*((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['v_skorost_mezhdu_plastinami_m_s']*params['y_n10']))))

def calc_n10_2(params):
    """
    Excel M248 / O248
    Формула (Excel): =IF(O243="","",(1-(($O$31-1)/($O$31+1))*O247^2)^(1/($O$31-1)))
    """
    return (((None) if (params['stupeni_n10_3']==None) else ((1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n10']**2)**(1/(params['koeffcient_adiabaty']-1)))))

def calc_n10_3(params):
    """
    Excel M249 / O249
    Формула (Excel): =IF(O243="","",1-(($O$31-1)/($O$31+1))*O247^2)
    """
    return (((None) if (params['stupeni_n10_3']==None) else (1-((params['koeffcient_adiabaty']-1)/(params['koeffcient_adiabaty']+1))*params['n10']**2)))

def calc_obtekateli(params):
    """
    Excel M253 / O253
    Формула (Excel): =E25
    """
    return (params['nalichie_obtekatelej_na_plastinah'])

def calc_r_gazovaya_postoyannaya_m2s2_k(params):
    """
    Excel M254 / O254
    Формула (Excel): =O29
    """
    return (params['gazovaya_postoyannaya_m2_s2_k'])

def calc_k_pokazatel_adiabaty(params):
    """
    Excel M255 / O255
    Формула (Excel): =$O$31
    """
    return (params['koeffcient_adiabaty'])

def calc_t_absolyutnaya_temperatura_pered_glushitelem_k(params):
    """
    Excel M256 / O256
    Формула (Excel): =O135
    """
    return (params['temperatura_k'])

def calc_g_rashod_sredy_kg_s(params):
    """
    Excel M257 / O257
    Формула (Excel): =O24
    """
    return (params['rashod_sredy_g_kg_s'])

def calc_d_vnutrennij_diametr_shg_m(params):
    """
    Excel M258 / O258
    Формула (Excel): =E27
    """
    return (params['vnutrennij_diametr_shumoglushitelya_korpus_m'])

def calc_pat_atmosfernoe_davlenie_pa(params):
    """
    Excel M259 / O259
    Формула (Excel): =E63
    """
    return (params['atmosfernoe_davlenie_pa'])


def calc_ss_summarnaya_ploschad_vseh_kanalov_m2(params):
    """
    Расчет суммарной площади всех каналов.

    Excel M260 / O260
    Формула: =SUM(O315,O330,O345,O360,O375,O390)
    """
    areas = [
        params.get('f_ploschad_kanala_m2_n1'),
        params.get('f_ploschad_kanala_m2_n2'),
        params.get('f_ploschad_kanala_m2_n3'),
        params.get('f_ploschad_kanala_m2_n4'),
        params.get('f_ploschad_kanala_m2_n5'),
        params.get('f_ploschad_kanala_m2_n6')
    ]

    return sum([area if area is not None else 0 for area in areas])

def calc_summ_diam(params):
    """
    Excel M261 / O261 (Σ), формула (5.198)
    =IF(AND(O388="";O343="";O373="";O358="";O328="");O315*SQRT(O313);
      IF(AND(O388="";O373="";O358="";O343="");SUM(O315*SQRT(O313);O330*SQRT(O328));
        IF(AND(O388="";O373="";O358="");SUM(O315*SQRT(O313);O330*SQRT(O328);O345*SQRT(O343));
          IF(AND(O388="";O373="");SUM(O315*SQRT(O313);O330*SQRT(O328);O345*SQRT(O343);O360*SQRT(O358));
            IF(O388="";
               SUM(O315*SQRT(O313);O330*SQRT(O328);O345*SQRT(O343);O360*SQRT(O358);O375*SQRT(O373));
               SUM(O315*SQRT(O313);O330*SQRT(O328);O345*SQRT(O343);O360*SQRT(O358);O375*SQRT(O373);O390*SQRT(O388))
            )
          )
        )
      )
    )
    """
    # Собираем список слагаемых по мере доступности
    terms = []

    if params.get("f_dh_0_5_n1") and params.get("dh_gidravlicheskij_diametr_m_n1"):
        terms.append(params["f_dh_0_5_n1"] * math.sqrt(params["dh_gidravlicheskij_diametr_m_n1"]))
    if params.get("f_dh_0_5_n2") and params.get("dh_gidravlicheskij_diametr_m_n2"):
        terms.append(params["f_dh_0_5_n2"] * math.sqrt(params["dh_gidravlicheskij_diametr_m_n2"]))
    if params.get("f_dh_0_5_n3") and params.get("dh_gidravlicheskij_diametr_m_n3"):
        terms.append(params["f_dh_0_5_n3"] * math.sqrt(params["dh_gidravlicheskij_diametr_m_n3"]))
    if params.get("f_dh_0_5_n4") and params.get("dh_gidravlicheskij_diametr_m_n4"):
        terms.append(params["f_dh_0_5_n4"] * math.sqrt(params["dh_gidravlicheskij_diametr_m_n4"]))
    if params.get("f_dh_0_5_n5") and params.get("dh_gidravlicheskij_diametr_m_n5"):
        terms.append(params["f_dh_0_5_n5"] * math.sqrt(params["dh_gidravlicheskij_diametr_m_n5"]))
    if params.get("f_dh_0_5_n6") and params.get("dh_gidravlicheskij_diametr_m_n6"):
        terms.append(params["f_dh_0_5_n6"] * math.sqrt(params["dh_gidravlicheskij_diametr_m_n6"]))

    return sum(terms) if terms else None

def calc_f_otnositelnaya_ploschad(params):
    """
    Excel M262 / O262
    Формула (Excel): =4*O260/(PI()*O258^2)
    """
    return (4*params['ss_summarnaya_ploschad_vseh_kanalov_m2']/(math.pi*params['d_vnutrennij_diametr_shg_m']**2))

def calc_l_dlina_kanalov_m(params):
    """
    Excel M263 / O263
    Формула (Excel): =E29
    """
    return (params['dlina_oblicovannyh_kanalov_m'])

def calc_pa_pa(params):
    """
    Excel M265 / O265
    Формула (Excel): =O286
    """
    return (params['pa_absolyutnoe_davlenie_za_stupenyu_zvukopogloscheniya_pa_2'])

def calc_ptr_pa(params):
    """
    Полное давление Ptr, Па
    Excel M266 / O266
    Формула (Excel):
    =IF(AND(O388="",O373="",O358="",O343="",O328=""),
        SQRT($O$257^2*$O$254*$O$256*$E$62*$O$263/(O316)^2+$O$265^2),
    IF(AND(O388="",O373="",O358="",O343=""),
        SQRT(O257^2*O254*O256*E62*O263/(SUM(O316,O331))^2+O265^2),
    IF(AND(O388="",O373="",O358=""),
        SQRT(O257^2*O254*O256*E62*O263/(SUM(O316,O331,O346))^2+O265^2),
    IF(AND(O388="",O373=""),
        SQRT(O257^2*O254*O256*E62*O263/(SUM(O316,O331,O346,O361))^2+O265^2),
    IF(O388="",
        SQRT(O257^2*O254*O256*E62*O263/(SUM(O316,O331,O346,O361,O376))^2+O265^2),
        SQRT(O257^2*O254*O256*E62*O263/(SUM(O316,O331,O346,O361,O376,O391))^2+O265^2))))))
    """
    g = params["g_rashod_sredy_kg_s"]
    R = params["r_gazovaya_postoyannaya_m2s2_k"]
    T = params["t_absolyutnaya_temperatura_pered_glushitelem_k"]
    f = params["koefficient_treniya"]
    L = params["l_dlina_kanalov_m"]
    pa = params["pa_pa"]

    # площади проходных сечений для разных каналов
    f_list = [
        params.get("f_dh_0_5_n1"),
        params.get("f_dh_0_5_n2"),
        params.get("f_dh_0_5_n3"),
        params.get("f_dh_0_5_n4"),
        params.get("f_dh_0_5_n5"),
        params.get("f_dh_0_5_n6"),
    ]

    # соответствующие гидравлические диаметры (по логике Excel проверялись на пустоту)
    dh_list = [
        params.get("dh_gidravlicheskij_diametr_m_n1"),
        params.get("dh_gidravlicheskij_diametr_m_n2"),
        params.get("dh_gidravlicheskij_diametr_m_n3"),
        params.get("dh_gidravlicheskij_diametr_m_n4"),
        params.get("dh_gidravlicheskij_diametr_m_n5"),
        params.get("dh_gidravlicheskij_diametr_m_n6"),
    ]

    # определяем сколько каналов реально учтено (в Excel смотрели "пустая ли ячейка")
    active_channels = 1
    for dh in dh_list[1:]:  # начинаем со второго, т.к. первый всегда есть
        if dh is not None:
            active_channels += 1
        else:
            break

    # берём соответствующие площади
    f_sum = sum([f for f in f_list[:active_channels] if f is not None])

    # формула давления
    ptr = math.sqrt((g**2 * R * T * f * L) / (f_sum**2) + pa**2)
    return ptr

def calc_pi3_davlenie_pered_stupenyu_zvukopogloscheniya_pa_2(params):
    """
    Excel M267 / O267
    Формула (Excel): =IF(O253="Есть",O266,IF(O253="Нет",O266+0.5*(1-O262)*O270*O269^2/2))
    """
    return (((params['ptr_pa']) if (params['obtekateli']=="Есть") else
             (((params['ptr_pa']+0.5*(1-params['f_otnositelnaya_ploschad'])*params['plotnost_rho_po_idealnomu_gazu']*params['v_aero']**2/2)
               if (params['obtekateli']=="Нет") else (None)))))


def calc_maksimalnaya_skorost_mezhdu_kasset_m_s(params):
    """
    Расчет максимальной скорости между кассетами.

    Excel M268 / O268
    Формула: =MAX(O320,O335,O350,O365,O380,O395)
    """
    speeds = [
        params.get('w_skorost_v_kanale_m_s_n1'),
        params.get('w_skorost_v_kanale_m_s_n2'),
        params.get('w_skorost_v_kanale_m_s_n3'),
        params.get('w_skorost_v_kanale_m_s_n4'),
        params.get('w_skorost_v_kanale_m_s_n5'),
        params.get('w_skorost_v_kanale_m_s_n6')
    ]

    valid_speeds = [speed for speed in speeds if speed is not None]

    return max(valid_speeds) if valid_speeds else 0
def calc_v_aero(params):
    """
    Excel M269 / O269
    Формула (Excel): =O257*O254*O256/(O266*O260)
    """
    return (params['g_rashod_sredy_kg_s']*params['r_gazovaya_postoyannaya_m2s2_k']*params['t_absolyutnaya_temperatura_pered_glushitelem_k']/(params['ptr_pa']*params['ss_summarnaya_ploschad_vseh_kanalov_m2']))


def calc_g_rashod_sredy_kg_s_2(params):
    """
    Excel M274 / O274
    Формула (Excel): =O24
    """
    return (params['rashod_sredy_g_kg_s'])

def calc_k_koefficient_adiabaty(params):
    """
    Excel M275 / O275
    Формула (Excel): =$O$31
    """
    return (params['koeffcient_adiabaty'])

def calc_r_individualnaya_gazovaya_postoyannaya_m2s2_k(params):
    """
    Excel M276 / O276
    Формула (Excel): =O29
    """
    return (params['gazovaya_postoyannaya_m2_s2_k'])

def calc_t_temperatura_sredy_k(params):
    """
    Excel M277 / O277
    Формула (Excel): =O135
    """
    return (params['temperatura_k'])

def calc_pat_atmosfernoe_davlenie_pa_2(params):
    """
    Excel M278 / O278
    Формула (Excel): 101325
    """
    return (params.get('pa_in_atm', 101325))

def calc_d_vnutrennij_diametr_korpusa_stupeni_zvukopogloscheniya_m(params):
    """
    Excel M279 / O279
    Формула (Excel): =E27
    """
    return (params['vnutrennij_diametr_shumoglushitelya_korpus_m'])

def calc_da_vnutrennij_diametr_vyhlopa_m(params):
    """
    Excel M280 / O280
    Формула (Excel): =O279-2*E28
    """
    return (params['d_vnutrennij_diametr_korpusa_stupeni_zvukopogloscheniya_m']-2*params['tolschina_oblicovki_m'])

def calc_hk_osevoe_rasstoyanie_ot_vyhodnogo_secheniya_korpusa_do_kryshki_m(params):
    """
    Excel M281 / O281
    Формула (Excel): =E35
    """
    return (params['rasstoyanie_ot_korpusa_do_kryshki_m'])

def calc_sk_ploschad_vyhodnogo_secheniya_kanala_korpusa_do_kryshki_m2(params):
    """
    Excel M282 / O282
    Формула (Excel): =PI()*O279*O281
    """
    return (math.pi*params['d_vnutrennij_diametr_korpusa_stupeni_zvukopogloscheniya_m']*params['hk_osevoe_rasstoyanie_ot_vyhodnogo_secheniya_korpusa_do_kryshki_m'])

def calc_sa(params):
    """
    Excel M283 / O283
    Формула (Excel): =PI()*O280^2/4
    """
    return (math.pi*params['da_vnutrennij_diametr_vyhlopa_m']**2/4)

def calc_pk_izbytochnoe_davlenie_pod_kryshkoj_pa_2(params):
    """
    Excel M284 / O284
    Формула (Excel): =O274^2*O276*O277/(2*O278*O282^2)
    """
    return (params['g_rashod_sredy_kg_s_2']**2*params['r_individualnaya_gazovaya_postoyannaya_m2s2_k']*params['t_temperatura_sredy_k']/(2*params['pat_atmosfernoe_davlenie_pa_2']*params['sk_ploschad_vyhodnogo_secheniya_kanala_korpusa_do_kryshki_m2']**2))

def calc_pa_izbytochnoe_davlenie_na_vyhode_iz_korpusa_za_stupenyu_zvukopogloscheniya_pa_2(params):
    """
    Excel M285 / O285
    Формула (Excel): =O284+((O274^2*O276*O277)/(2*(O278+O284)*O283^2))*(1-(O280/O279)^4)
    """
    return (params['pk_izbytochnoe_davlenie_pod_kryshkoj_pa_2']+((params['g_rashod_sredy_kg_s_2']**2*params['r_individualnaya_gazovaya_postoyannaya_m2s2_k']*params['t_temperatura_sredy_k'])/(2*(params['pat_atmosfernoe_davlenie_pa_2']+params['pk_izbytochnoe_davlenie_pod_kryshkoj_pa_2'])*params['sa']**2))*(1-(params['da_vnutrennij_diametr_vyhlopa_m']/params['d_vnutrennij_diametr_korpusa_stupeni_zvukopogloscheniya_m'])**4))

def calc_pa_absolyutnoe_davlenie_za_stupenyu_zvukopogloscheniya_pa_2(params):
    """
    Excel M286 / O286
    Формула (Excel): =O285+O278
    """
    return (params['pa_izbytochnoe_davlenie_na_vyhode_iz_korpusa_za_stupenyu_zvukopogloscheniya_pa_2']+params['pat_atmosfernoe_davlenie_pa_2'])

def calc_pk(params):
    """
    Excel M290 / O290
    Формула (Excel): =O284+O278
    """
    return (params['pk_izbytochnoe_davlenie_pod_kryshkoj_pa_2']+params['pat_atmosfernoe_davlenie_pa_2'])

def calc_wa_skorost_na_vyhode_iz_korpusa_m_s_2(params):
    """
    Excel M291 / O291
    Формула (Excel): =(O274*O276*O277)/(O290*O283)
    """
    return ((params['g_rashod_sredy_kg_s_2']*params['r_individualnaya_gazovaya_postoyannaya_m2s2_k']*params['t_temperatura_sredy_k'])/(params['pk']*params['sa']))

def calc_wk_skorost_na_vyhlope_v_atmosferu_m_s_2(params):
    """
    Excel M292 / O292
    Формула (Excel): =(O274*O276*O277)/(O278*O282)
    """
    return ((params['g_rashod_sredy_kg_s_2']*params['r_individualnaya_gazovaya_postoyannaya_m2s2_k']*params['t_temperatura_sredy_k'])/(params['pat_atmosfernoe_davlenie_pa_2']*params['sk_ploschad_vyhodnogo_secheniya_kanala_korpusa_do_kryshki_m2']))

def calc_ma_chislo_maha_na_vyhode_iz_korpusa_2(params):
    """
    Excel M293 / O293
    Формула (Excel): =O291/SQRT(O275*O276*O277)
    """
    return (params['wa_skorost_na_vyhode_iz_korpusa_m_s_2']/math.sqrt(params['k_koefficient_adiabaty']*params['r_individualnaya_gazovaya_postoyannaya_m2s2_k']*params['t_temperatura_sredy_k']))

def calc_mk_chislo_maha_na_vyhlope_v_atmosferu_2(params):
    """
    Excel M294 / O294
    Формула (Excel): =O292/SQRT(O275*O276*O277)
    """
    return (params['wk_skorost_na_vyhlope_v_atmosferu_m_s_2']/math.sqrt(params['k_koefficient_adiabaty']*params['r_individualnaya_gazovaya_postoyannaya_m2s2_k']*params['t_temperatura_sredy_k']))

def calc_k_ma(params):
    """
    Excel M295 / O295
    Формула (Excel): =IF(O293<=SQRT(0.8),8*10^(-5)*O293^3,IF(AND(O293>SQRT(0.8),O293<=20^0.2),10^(-4)*O293^5,IF(O293>20^0.2,2*10^(-3))))
    """
    return (((8*10**(-5)*params['ma_chislo_maha_na_vyhode_iz_korpusa_2']**3) if (params['ma_chislo_maha_na_vyhode_iz_korpusa_2']<=math.sqrt(0.8)) else (((10**(-4)*params['ma_chislo_maha_na_vyhode_iz_korpusa_2']**5) if ((params['ma_chislo_maha_na_vyhode_iz_korpusa_2']>math.sqrt(0.8) and params['ma_chislo_maha_na_vyhode_iz_korpusa_2']<=20**0.2)) else (((2*10**(-3)) if (params['ma_chislo_maha_na_vyhode_iz_korpusa_2']>20**0.2) else (None)))))))

def calc_k_mk(params):
    """
    Excel M296 / O296
    Формула (Excel): =IF(O294<=SQRT(0.8),8*10^(-5)*O294^3,IF(AND(O294>SQRT(0.8),O294<=20^0.2),10^(-4)*O294^5,IF(O294>20^0.2,2*10^(-3))))
    """
    return (((8*10**(-5)*params['mk_chislo_maha_na_vyhlope_v_atmosferu_2']**3) if (params['mk_chislo_maha_na_vyhlope_v_atmosferu_2']<=math.sqrt(0.8)) else (((10**(-4)*params['mk_chislo_maha_na_vyhlope_v_atmosferu_2']**5) if ((params['mk_chislo_maha_na_vyhlope_v_atmosferu_2']>math.sqrt(0.8) and params['mk_chislo_maha_na_vyhlope_v_atmosferu_2']<=20**0.2)) else (((2*10**(-3)) if (params['mk_chislo_maha_na_vyhlope_v_atmosferu_2']>20**0.2) else (None)))))))

def calc_wa_moschnost_shuma_na_vyhode_iz_korpusa_vt(params):
    """
    Excel M297 / O297
    Формула (Excel): =O295*O274*O291^2/2
    """
    return (params['k_ma']*params['g_rashod_sredy_kg_s_2']*params['wa_skorost_na_vyhode_iz_korpusa_m_s_2']**2/2)

def calc_wk_moschnost_shuma_na_vyhode_iz_pod_kryshki_vt(params):
    """
    Excel M298 / O298
    Формула (Excel): =O296*O274*O292^2/2
    """
    return (params['k_mk']*params['g_rashod_sredy_kg_s_2']*params['wk_skorost_na_vyhlope_v_atmosferu_m_s_2']**2/2)

def calc_lwa_uzm_generiruemyj_istecheniem_iz_korpusa_db(params):
    """
    Excel M299 / O299
    Формула (Excel): =10*LOG10(O297/(10^(-12)))
    """
    return (10*math.log10(params['wa_moschnost_shuma_na_vyhode_iz_korpusa_vt']/(10**(-12))))

def calc_lwk_uzm_generiruemyj_istecheniem_iz_pod_kryshki_db(params):
    """
    Excel M300 / O300
    Формула (Excel): =10*LOG10(O298/(10^(-12)))
    """
    return (10*math.log10(params['wk_moschnost_shuma_na_vyhode_iz_pod_kryshki_vt']/(10**(-12))))


def calc_gas_flow_function(pressure_ratio, gamma):
    """
    Газодинамическая функция расхода
    Возвращает 1 в режиме критического истечения, иначе изоэнтропическая функция.
    """
    critical_ratio = (1 - (gamma - 1) / (gamma + 1)) ** (1 / (gamma - 1))
    if pressure_ratio > critical_ratio:
        return (pressure_ratio ** (1 / gamma) / critical_ratio) * math.sqrt(
            (gamma + 1) / (gamma - 1) * (1 - pressure_ratio ** ((gamma - 1) / gamma))
        )
    return 1


def calc_dinamicheskaya_nagruzka_na_drosselnyj_blok_kn_2(params):
    """
    Excel M304 / O304
    Формула (Excel): =(($O$31+1)/(2*$O$31)*O24*O28*(O16+1/O16)-O153*(PI()*E36^2/4))*0.001
    """
    return (((params['koeffcient_adiabaty']+1)/(2*params['koeffcient_adiabaty'])*params['rashod_sredy_g_kg_s']*params['kriticheskaya_skorost_skr_m_s']*(params['λ']+1/params['λ'])-params['pi3_davlenie_pered_stupenyu_zvukopogloscheniya_pa']*(math.pi*params['vyhodnoj_vneshnij_diametr_m']**2/4))*0.001)

def calc_dinamicheskaya_nagruzka_na_stupen_zvukopogloscheniya_kn_2(params):
    """
    Excel M305 / O305
    Формула (Excel): =(PI()*O258^2/4)*(O267-O265)*0.001
    """
    return ((math.pi*params['d_vnutrennij_diametr_shg_m']**2/4)*(params['pi3_davlenie_pered_stupenyu_zvukopogloscheniya_pa_2']-params['pa_pa'])*0.001)

def calc_dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_bokovom_vyhlope_kn_2(params):
    """
    Excel M306 / O306
    Формула (Excel): =(PI()*POWER(O279,2)/4)*O284*0.001
    """
    return ((math.pi*power(params['d_vnutrennij_diametr_korpusa_stupeni_zvukopogloscheniya_m'],2)/4)*params['pk_izbytochnoe_davlenie_pod_kryshkoj_pa_2']*0.001)

def calc_dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_osevom_vyhlope_kn_2(params):
    """
    Excel M307 / O307
    Формула (Excel): =IF((PI()*POWER(O279,2)/4-O282)<0,0,(PI()*POWER(O279,2)/4-O282)*O284*0.001)
    """
    return (((0) if ((math.pi*power(params['d_vnutrennij_diametr_korpusa_stupeni_zvukopogloscheniya_m'],2)/4-params['sk_ploschad_vyhodnogo_secheniya_kanala_korpusa_do_kryshki_m2'])<0) else ((math.pi*power(params['d_vnutrennij_diametr_korpusa_stupeni_zvukopogloscheniya_m'],2)/4-params['sk_ploschad_vyhodnogo_secheniya_kanala_korpusa_do_kryshki_m2'])*params['pk_izbytochnoe_davlenie_pod_kryshkoj_pa_2']*0.001)))

def calc_davlenie_na_dnische_drosselnogo_bloka_mpa(params):
    """
    Excel M308 / O308
    Формула (Excel): =O170*10^3/(PI()*(E36-2*(E37*10^-3))^2/4)*10^-6
    """
    return (params['dinamicheskaya_nagruzka_na_drosselnyj_blok_kn']*10**3/(math.pi*(params['vyhodnoj_vneshnij_diametr_m']-2*(params['tolschina_stenki_mm']*10**-3))**2/4)*10**-6)

def calc_r_vnutrennij_radius_m_n1(params):
    """
    Excel M311 / O311
    Формула (Excel): =IF(AND(E42=0,E41>=1),E43*0.001,0)
    """
    return (((params['t1_tolschina_1_kassety_mm']*0.001) if ((params['r1_vnutrennij_radius_1_kassety_mm']==0 and params['kolichestvo_kasset']>=1)) else (0)))

def calc_r_naruzhnyj_radius_m_n1(params):
    """
    Excel M312 / O312
    Формула (Excel): =IF(AND(E42=0,E41>=1),O311+E44*0.001,IF(E42>0,E42*0.001))
    """
    return (((params['r_vnutrennij_radius_m_n1']+params['r2_rasstoyanie_m_u_1_i_2_kassetoj_mm']*0.001) if ((params['r1_vnutrennij_radius_1_kassety_mm']==0 and params['kolichestvo_kasset']>=1)) else (((params['r1_vnutrennij_radius_1_kassety_mm']*0.001) if (params['r1_vnutrennij_radius_1_kassety_mm']>0) else (None)))))

def calc_dh_gidravlicheskij_diametr_m_n1(params):
    """
    Excel M313 / O313
    Формула (Excel): =2*(O312-O311)
    """
    return (2*(params['r_naruzhnyj_radius_m_n1']-params['r_vnutrennij_radius_m_n1']))

def calc_d_shirina_kanala_m_n1(params):
    """
    Excel M314 / O314
    Формула (Excel): =O312-O311
    """
    return (params['r_naruzhnyj_radius_m_n1']-params['r_vnutrennij_radius_m_n1'])

def calc_f_ploschad_kanala_m2_n1(params):
    """
    Excel M315 / O315
    Формула (Excel): =PI()*(O312^2-O311^2)
    """
    return (math.pi*(params['r_naruzhnyj_radius_m_n1']**2-params['r_vnutrennij_radius_m_n1']**2))

def calc_f_dh_0_5_n1(params):
    """
    Excel M316 / O316
    Формула (Excel): =O315*SQRT(O313)
    """
    return (params['f_ploschad_kanala_m2_n1']*math.sqrt(params['dh_gidravlicheskij_diametr_m_n1']))

def calc_h_srednyaya_tolschina_plastin_m_n1(params):
    """
    Excel M317 / O317
    Формула (Excel): =IF(E42=0,(O311*E43*2*0.001+O312*E45*0.001)/(O311+O312),(O312*E43*0.001)/O312)
    """
    return ((((params['r_vnutrennij_radius_m_n1']*params['t1_tolschina_1_kassety_mm']*2*0.001+params['r_naruzhnyj_radius_m_n1']*params['t2_tolschina_2_kassety_mm']*0.001)/(params['r_vnutrennij_radius_m_n1']+params['r_naruzhnyj_radius_m_n1'])) if (params['r1_vnutrennij_radius_1_kassety_mm']==0) else ((params['r_naruzhnyj_radius_m_n1']*params['t1_tolschina_1_kassety_mm']*0.001)/params['r_naruzhnyj_radius_m_n1'])))


def calc_pd_skorostnoj_napor_na_vyhode_pa_n1(params):
    """
    Расчет скоростного напора на выходе для первой кассеты.

    Excel M318 / O318
    Формула: =O257^2*O313*O254*O256/(2*O259*O261^2)
    """
    g = params['g_rashod_sredy_kg_s']
    dh = params['dh_gidravlicheskij_diametr_m_n1']
    r = params['r_gazovaya_postoyannaya_m2s2_k']
    t = params['t_absolyutnaya_temperatura_pered_glushitelem_k']
    pat = params['pat_atmosfernoe_davlenie_pa']
    summ_diam = params['summ_diam']

    numerator = g ** 2 * dh * r * t
    denominator = 2 * pat * summ_diam ** 2

    return numerator / denominator


def calc_g_rashod_v_kanale_kg_s_n1(params):
    """
    Excel M319 / O319
    Формула (Excel): =(O257*O315*SQRT(O313))/O261
    """
    return ((params['g_rashod_sredy_kg_s']*params['f_ploschad_kanala_m2_n1']*math.sqrt(params['dh_gidravlicheskij_diametr_m_n1']))/params['summ_diam'])

def calc_w_skorost_v_kanale_m_s_n1(params):
    """
    Excel M320 / O320
    Формула (Excel): =(O319*O254*O256)/(O259*O315)
    """
    return ((params['g_rashod_v_kanale_kg_s_n1']*params['r_gazovaya_postoyannaya_m2s2_k']*params['t_absolyutnaya_temperatura_pered_glushitelem_k'])/(params['pat_atmosfernoe_davlenie_pa']*params['f_ploschad_kanala_m2_n1']))

def calc_m_chislo_maha_v_kanale_n1(params):
    """
    Excel M321 / O321
    Формула (Excel): =O320/SQRT(O255*O254*O256)
    """
    return (params['w_skorost_v_kanale_m_s_n1']/math.sqrt(params['k_pokazatel_adiabaty']*params['r_gazovaya_postoyannaya_m2s2_k']*params['t_absolyutnaya_temperatura_pered_glushitelem_k']))

def calc_k_m_n1(params):
    """
    Excel M322 / O322
    Формула (Excel): =IF(O321<=SQRT(0.8),8*10^(-5)*O321^3,IF(AND(O321>SQRT(0.8),O321<=20^0.2),10^(-4)*O321^5,IF(O321>20^0.2,2*10^(-3))))
    """
    return (((8*10**(-5)*params['m_chislo_maha_v_kanale_n1']**3) if (params['m_chislo_maha_v_kanale_n1']<=math.sqrt(0.8)) else (((10**(-4)*params['m_chislo_maha_v_kanale_n1']**5) if ((params['m_chislo_maha_v_kanale_n1']>math.sqrt(0.8) and params['m_chislo_maha_v_kanale_n1']<=20**0.2)) else (((2*10**(-3)) if (params['m_chislo_maha_v_kanale_n1']>20**0.2) else (None)))))))

def calc_ds_n1(params):
    """
    Excel M323 / O323
    Формула (Excel): =MIN(O314,O317)
    """
    return (min(params['d_shirina_kanala_m_n1'], params['h_srednyaya_tolschina_plastin_m_n1']))

def calc_ws_moschnost_shuma_na_vyhode_kanala_vt_n1(params):
    """
    Excel M324 / O324
    Формула (Excel): =O322*O319*(O320^2)/2*SQRT((O312+O311)/(O312-O311))
    """
    return (params['k_m_n1']*params['g_rashod_v_kanale_kg_s_n1']*(params['w_skorost_v_kanale_m_s_n1']**2)/2*math.sqrt((params['r_naruzhnyj_radius_m_n1']+params['r_vnutrennij_radius_m_n1'])/(params['r_naruzhnyj_radius_m_n1']-params['r_vnutrennij_radius_m_n1'])))

def calc_lws_n1(params):
    """
    Excel M325 / O325
    Формула (Excel): =10*LOG10(O324/(10^(-12)))
    """
    return (10*math.log10(params['ws_moschnost_shuma_na_vyhode_kanala_vt_n1']/(10**(-12))))


def calc_r_vnutrennij_radius_m_n2(params: dict) -> Optional[float]:
    """
    Расчет внутреннего радиуса для второй кассеты.

    Excel M326 / O326
    Формула: =IF(AND(E42=0,E41=1),"",IF(AND(E42=0,E41>=2),O312+E45*0.001,IF(AND(E42>0,E41>=1),O312+E43*0.001)))

    Args:
        params: Словарь с входными параметрами, должен содержать:
            - r1_vnutrennij_radius_1_kassety_mm: внутренний радиус 1 кассеты, мм
            - kolichestvo_kasset: количество кассет, шт
            - r_naruzhnyj_radius_m_n1: наружный радиус 1 кассеты, м
            - t2_tolschina_2_kassety_mm: толщина 2 кассеты, мм
            - t1_tolschina_1_kassety_mm: толщина 1 кассеты, мм

    Returns:
        Optional[float]: Внутренний радиус второй кассеты в метрах или None, если не применимо

    Raises:
        KeyError: Если отсутствуют необходимые параметры
    """
    # Проверка наличия необходимых параметров
    required_params = [
        'r1_vnutrennij_radius_1_kassety_mm',
        'kolichestvo_kasset',
        'r_naruzhnyj_radius_m_n1'
    ]

    for param in required_params:
        if param not in params:
            raise KeyError(f"Отсутствует обязательный параметр: {param}")

    r1_mm = params['r1_vnutrennij_radius_1_kassety_mm']
    kolichestvo = params['kolichestvo_kasset']
    r_naruzhnyj_n1 = params['r_naruzhnyj_radius_m_n1']

    # Случай 1: r1 = 0 и количество кассет = 1
    if r1_mm == 0 and kolichestvo == 1:
        return None

    # Случай 2: r1 = 0 и количество кассет >= 2
    elif r1_mm == 0 and kolichestvo >= 2:
        if 't2_tolschina_2_kassety_mm' not in params:
            raise KeyError("Отсутствует параметр: t2_tolschina_2_kassety_mm")
        return r_naruzhnyj_n1 + params['t2_tolschina_2_kassety_mm'] * 0.001

    # Случай 3: r1 > 0 и количество кассет >= 1
    elif r1_mm > 0 and kolichestvo >= 1:
        if 't1_tolschina_1_kassety_mm' not in params:
            raise KeyError("Отсутствует параметр: t1_tolschina_1_kassety_mm")
        return r_naruzhnyj_n1 + params['t1_tolschina_1_kassety_mm'] * 0.001

    # Все остальные случаи
    else:
        return None


def calc_r_naruzhnyj_radius_m_n2(params):
    """
    Excel M327 / O327
    Формула (Excel): =IF(AND(E42=0,E41=1),"",IF(AND(E42=0,E41>=2),O326+E46*0.001,IF(AND(E42>0,E41>=1),O326+E44*0.001)))
    """
    return (((None) if ((params['r1_vnutrennij_radius_1_kassety_mm']==0 and params['kolichestvo_kasset']==1)) else (((params['r_vnutrennij_radius_m_n2']+params['r3_rasstoyanie_m_u_2_kassetoj_i_oblicovkoj_mm']*0.001) if ((params['r1_vnutrennij_radius_1_kassety_mm']==0 and params['kolichestvo_kasset']>=2)) else (((params['r_vnutrennij_radius_m_n2']+params['r2_rasstoyanie_m_u_1_i_2_kassetoj_mm']*0.001) if ((params['r1_vnutrennij_radius_1_kassety_mm']>0 and params['kolichestvo_kasset']>=1)) else (None)))))))

def calc_dh_gidravlicheskij_diametr_m_n2(params):
    """
    Excel M328 / O328
    Формула (Excel): =IF(AND(O326="",O327=""),"",2*(O327-O326))
    """
    return (((None) if ((params['r_vnutrennij_radius_m_n2']==None and params['r_naruzhnyj_radius_m_n2']==None)) else (2*(params['r_naruzhnyj_radius_m_n2']-params['r_vnutrennij_radius_m_n2']))))

def calc_d_shirina_kanala_m_n2(params):
    """
    Excel M329 / O329
    Формула (Excel): =IF(AND(O327="",O326=""),"",O327-O326)
    """
    return (((None) if ((params['r_naruzhnyj_radius_m_n2']==None and params['r_vnutrennij_radius_m_n2']==None)) else (params['r_naruzhnyj_radius_m_n2']-params['r_vnutrennij_radius_m_n2'])))

def calc_f_ploschad_kanala_m2_n2(params):
    """
    Excel M330 / O330
    Формула (Excel): =IF(AND(O326="",O327=""),"",PI()*(O327^2-O326^2))
    """
    return (((None) if ((params['r_vnutrennij_radius_m_n2']==None and params['r_naruzhnyj_radius_m_n2']==None)) else (math.pi*(params['r_naruzhnyj_radius_m_n2']**2-params['r_vnutrennij_radius_m_n2']**2))))

def calc_f_dh_0_5_n2(params):
    """
    Excel M331 / O331
    Формула (Excel): =IF(O328="","",O330*SQRT(O328))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n2']==None) else (params['f_ploschad_kanala_m2_n2']*math.sqrt(params['dh_gidravlicheskij_diametr_m_n2']))))

def calc_h_srednyaya_tolschina_plastin_m_n2(params):
    """
    Excel M332 / O332
    Формула (Excel): =IF(O326="","",IF(E42=0,(O326*E45*0.001+O327*E47*0.001)/(O326+O327),(O326*E43*0.001+O327*E45*0.001)/(O326+O327)))
    """
    return (((None) if (params['r_vnutrennij_radius_m_n2']==None) else ((((params['r_vnutrennij_radius_m_n2']*params['t2_tolschina_2_kassety_mm']*0.001+params['r_naruzhnyj_radius_m_n2']*params['t3_tolschina_oblicovki_mm']*0.001)/(params['r_vnutrennij_radius_m_n2']+params['r_naruzhnyj_radius_m_n2'])) if (params['r1_vnutrennij_radius_1_kassety_mm']==0) else ((params['r_vnutrennij_radius_m_n2']*params['t1_tolschina_1_kassety_mm']*0.001+params['r_naruzhnyj_radius_m_n2']*params['t2_tolschina_2_kassety_mm']*0.001)/(params['r_vnutrennij_radius_m_n2']+params['r_naruzhnyj_radius_m_n2']))))))

def calc_pd_skorostnoj_napor_na_vyhode_pa_n2(params):
    """
    Excel M333 / O333
    Формула (Excel): =IF(O328="","",O257^2*O328*O254*O256/(2*O259*O261^2))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n2']==None) else (params['g_rashod_sredy_kg_s']**2*params['dh_gidravlicheskij_diametr_m_n2']*params['r_gazovaya_postoyannaya_m2s2_k']*params['t_absolyutnaya_temperatura_pered_glushitelem_k']/(2*params['pat_atmosfernoe_davlenie_pa']*params['summ_diam']**2))))

def calc_g_rashod_v_kanale_kg_s_n2(params):
    """
    Excel M334 / O334
    Формула (Excel): =IF(O328="","",(O257*O330*SQRT(O328))/summ_diam)
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n2']==None) else ((params['g_rashod_sredy_kg_s']*params['f_ploschad_kanala_m2_n2']*math.sqrt(params['dh_gidravlicheskij_diametr_m_n2']))/params['summ_diam'])))

def calc_w_skorost_v_kanale_m_s_n2(params):
    """
    Excel M335 / O335
    Формула (Excel): =IF(O328="","",(O334*O254*O256)/(O259*O330))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n2']==None) else ((params['g_rashod_v_kanale_kg_s_n2']*params['r_gazovaya_postoyannaya_m2s2_k']*params['t_absolyutnaya_temperatura_pered_glushitelem_k'])/(params['pat_atmosfernoe_davlenie_pa']*params['f_ploschad_kanala_m2_n2']))))

def calc_m_chislo_maha_v_kanale_n2(params):
    """
    Excel M336 / O336
    Формула (Excel): =IF(O328="","",O335/SQRT(O255*O254*O256))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n2']==None) else (params['w_skorost_v_kanale_m_s_n2']/math.sqrt(params['k_pokazatel_adiabaty']*params['r_gazovaya_postoyannaya_m2s2_k']*params['t_absolyutnaya_temperatura_pered_glushitelem_k']))))

def calc_k_m_n2(params):
    """
    Excel M337 / O337
    Формула (Excel): =IF(O336="","",IF(O336<=SQRT(0.8),8*10^(-5)*O336^3,IF(AND(O336>SQRT(0.8),O336<=20^0.2),10^(-4)*O336^5,IF(O336>20^0.2,2*10^(-3)))))
    """
    return (((None) if (params['m_chislo_maha_v_kanale_n2']==None) else (((8*10**(-5)*params['m_chislo_maha_v_kanale_n2']**3) if (params['m_chislo_maha_v_kanale_n2']<=math.sqrt(0.8)) else (((10**(-4)*params['m_chislo_maha_v_kanale_n2']**5) if ((params['m_chislo_maha_v_kanale_n2']>math.sqrt(0.8) and params['m_chislo_maha_v_kanale_n2']<=20**0.2)) else (((2*10**(-3)) if (params['m_chislo_maha_v_kanale_n2']>20**0.2) else (None)))))))))

def calc_ds_n2(params):
    """
    Excel M338 / O338
    Формула (Excel): =IF(O329="","",MIN(O329,O332))
    """
    return (((None) if (params['d_shirina_kanala_m_n2']==None) else (min(params['d_shirina_kanala_m_n2'], params['h_srednyaya_tolschina_plastin_m_n2']))))

def calc_ws_moschnost_shuma_na_vyhode_kanala_vt_n2(params):
    """
    Excel M339 / O339
    Формула (Excel): =IF(O334="","",O337*O334*(O335^2)/2*SQRT((O327+O326)/(O327-O326)))
    """
    return (((None) if (params['g_rashod_v_kanale_kg_s_n2']==None) else (params['k_m_n2']*params['g_rashod_v_kanale_kg_s_n2']*(params['w_skorost_v_kanale_m_s_n2']**2)/2*math.sqrt((params['r_naruzhnyj_radius_m_n2']+params['r_vnutrennij_radius_m_n2'])/(params['r_naruzhnyj_radius_m_n2']-params['r_vnutrennij_radius_m_n2'])))))

def calc_lws_n2(params):
    """
    Excel M340 / O340
    Формула (Excel): =IF(O339="","",10*LOG10(O339/(10^(-12))))
    """
    return (((None) if (params['ws_moschnost_shuma_na_vyhode_kanala_vt_n2']==None) else (10*math.log10(params['ws_moschnost_shuma_na_vyhode_kanala_vt_n2']/(10**(-12))))))

def calc_r_vnutrennij_radius_m_n3(params):
    """
    Excel M341 / O341
    Формула (Excel): =IF(AND(E42=0,E41<=2),"",IF(AND(E42=0,E41>=3),O327+E47*0.001,IF(AND(E42>0,E41<=1),"",IF(AND(E42>0,E41>=2),O327+E45*0.001))))
    """
    return (((None) if ((params['r1_vnutrennij_radius_1_kassety_mm']==0 and params['kolichestvo_kasset']<=2)) else (((params['r_naruzhnyj_radius_m_n2']+params['t3_tolschina_oblicovki_mm']*0.001) if ((params['r1_vnutrennij_radius_1_kassety_mm']==0 and params['kolichestvo_kasset']>=3)) else (((None) if ((params['r1_vnutrennij_radius_1_kassety_mm']>0 and params['kolichestvo_kasset']<=1)) else (((params['r_naruzhnyj_radius_m_n2']+params['t2_tolschina_2_kassety_mm']*0.001) if ((params['r1_vnutrennij_radius_1_kassety_mm']>0 and params['kolichestvo_kasset']>=2)) else (None)))))))))

def calc_r_naruzhnyj_radius_m_n3(params):
    """
    Excel M342 / O342
    Формула (Excel): =IF(AND(E42=0,E41<=2),"",IF(AND(E42=0,E41>=3),O341+E48*0.001,IF(AND(E42>0,E41<=1),"",IF(AND(E42>0,E41>=2),O341+E46*0.001))))
    """
    return (((None) if ((params['r1_vnutrennij_radius_1_kassety_mm']==0 and params['kolichestvo_kasset']<=2)) else (((params['r_vnutrennij_radius_m_n3']+params['e48']*0.001) if ((params['r1_vnutrennij_radius_1_kassety_mm']==0 and params['kolichestvo_kasset']>=3)) else (((None) if ((params['r1_vnutrennij_radius_1_kassety_mm']>0 and params['kolichestvo_kasset']<=1)) else (((params['r_vnutrennij_radius_m_n3']+params['r3_rasstoyanie_m_u_2_kassetoj_i_oblicovkoj_mm']*0.001) if ((params['r1_vnutrennij_radius_1_kassety_mm']>0 and params['kolichestvo_kasset']>=2)) else (None)))))))))

def calc_dh_gidravlicheskij_diametr_m_n3(params):
    """
    Excel M343 / O343
    Формула (Excel): =IF(AND(O341="",O342=""),"",2*(O342-O341))
    """
    return (((None) if ((params['r_vnutrennij_radius_m_n3']==None and params['r_naruzhnyj_radius_m_n3']==None)) else (2*(params['r_naruzhnyj_radius_m_n3']-params['r_vnutrennij_radius_m_n3']))))

def calc_d_shirina_kanala_m_n3(params):
    """
    Excel M344 / O344
    Формула (Excel): =IF(AND(O341="",O342=""),"",O342-O341)
    """
    return (((None) if ((params['r_vnutrennij_radius_m_n3']==None and params['r_naruzhnyj_radius_m_n3']==None)) else (params['r_naruzhnyj_radius_m_n3']-params['r_vnutrennij_radius_m_n3'])))

def calc_f_ploschad_kanala_m2_n3(params):
    """
    Excel M345 / O345
    Формула (Excel): =IF(AND(O341="",O342=""),"",PI()*(O342^2-O341^2))
    """
    return (((None) if ((params['r_vnutrennij_radius_m_n3']==None and params['r_naruzhnyj_radius_m_n3']==None)) else (math.pi*(params['r_naruzhnyj_radius_m_n3']**2-params['r_vnutrennij_radius_m_n3']**2))))

def calc_f_dh_0_5_n3(params):
    """
    Excel M346 / O346
    Формула (Excel): =IF(O343="","",O345*SQRT(O343))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n3']==None) else (params['f_ploschad_kanala_m2_n3']*math.sqrt(params['dh_gidravlicheskij_diametr_m_n3']))))

def calc_h_srednyaya_tolschina_plastin_m_n3(params):
    """
    Excel M347 / O347
    Формула (Excel): =IF(O344="","",IF(E42=0,(O341*E47*0.001+O342*E49*0.001)/(O341+O342),(O341*E45*0.001+O342*E47*0.001)/(O341+O342)))
    """
    return (((None) if (params['d_shirina_kanala_m_n3']==None) else ((((params['r_vnutrennij_radius_m_n3']*params['t3_tolschina_oblicovki_mm']*0.001+params['r_naruzhnyj_radius_m_n3']*params['e49']*0.001)/(params['r_vnutrennij_radius_m_n3']+params['r_naruzhnyj_radius_m_n3'])) if (params['r1_vnutrennij_radius_1_kassety_mm']==0) else ((params['r_vnutrennij_radius_m_n3']*params['t2_tolschina_2_kassety_mm']*0.001+params['r_naruzhnyj_radius_m_n3']*params['t3_tolschina_oblicovki_mm']*0.001)/(params['r_vnutrennij_radius_m_n3']+params['r_naruzhnyj_radius_m_n3']))))))

def calc_pd_skorostnoj_napor_na_vyhode_pa_n3(params):
    """
    Excel M348 / O348
    Формула (Excel): =IF(O343="","",O257^2*O343*O254*O256/(2*O259*summ_diam^2))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n3']==None) else (params['g_rashod_sredy_kg_s']**2*params['dh_gidravlicheskij_diametr_m_n3']*params['r_gazovaya_postoyannaya_m2s2_k']*params['t_absolyutnaya_temperatura_pered_glushitelem_k']/(2*params['pat_atmosfernoe_davlenie_pa']*params['summ_diam']**2))))

def calc_g_rashod_v_kanale_kg_s_n3(params):
    """
    Excel M349 / O349
    Формула (Excel): =IF(O343="","",(O257*O345*SQRT(O343))/summ_diam)
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n3']==None) else ((params['g_rashod_sredy_kg_s']*params['f_ploschad_kanala_m2_n3']*math.sqrt(params['dh_gidravlicheskij_diametr_m_n3']))/params['summ_diam'])))

def calc_w_skorost_v_kanale_m_s_n3(params):
    """
    Excel M350 / O350
    Формула (Excel): =IF(O343="","",(O349*O254*O256)/(O259*O345))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n3']==None) else ((params['g_rashod_v_kanale_kg_s_n3']*params['r_gazovaya_postoyannaya_m2s2_k']*params['t_absolyutnaya_temperatura_pered_glushitelem_k'])/(params['pat_atmosfernoe_davlenie_pa']*params['f_ploschad_kanala_m2_n3']))))

def calc_m_chislo_maha_v_kanale_n3(params):
    """
    Excel M351 / O351
    Формула (Excel): =IF(O343="","",O350/SQRT(O255*O254*O256))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n3']==None) else (params['w_skorost_v_kanale_m_s_n3']/math.sqrt(params['k_pokazatel_adiabaty']*params['r_gazovaya_postoyannaya_m2s2_k']*params['t_absolyutnaya_temperatura_pered_glushitelem_k']))))

def calc_k_m_n3(params):
    """
    Excel M352 / O352
    Формула (Excel): =IF(O351="","",IF(O351<=SQRT(0.8),8*10^(-5)*O351^3,IF(AND(O351>SQRT(0.8),O351<=20^0.2),10^(-4)*O351^5,IF(O351>20^0.2,2*10^(-3)))))
    """
    return (((None) if (params['m_chislo_maha_v_kanale_n3']==None) else (((8*10**(-5)*params['m_chislo_maha_v_kanale_n3']**3) if (params['m_chislo_maha_v_kanale_n3']<=math.sqrt(0.8)) else (((10**(-4)*params['m_chislo_maha_v_kanale_n3']**5) if ((params['m_chislo_maha_v_kanale_n3']>math.sqrt(0.8) and params['m_chislo_maha_v_kanale_n3']<=20**0.2)) else (((2*10**(-3)) if (params['m_chislo_maha_v_kanale_n3']>20**0.2) else (None)))))))))

def calc_ds_n3(params):
    """
    Excel M353 / O353
    Формула (Excel): =IF(O344="","",MIN(O344,O347))
    """
    return (((None) if (params['d_shirina_kanala_m_n3']==None) else (min(params['d_shirina_kanala_m_n3'], params['h_srednyaya_tolschina_plastin_m_n3']))))

def calc_ws_moschnost_shuma_na_vyhode_kanala_vt_n3(params):
    """
    Excel M354 / O354
    Формула (Excel): =IF(O349="","",O352*O349*(O350^2)/2*SQRT((O342+O341)/(O342-O341)))
    """
    return (((None) if (params['g_rashod_v_kanale_kg_s_n3']==None) else (params['k_m_n3']*params['g_rashod_v_kanale_kg_s_n3']*(params['w_skorost_v_kanale_m_s_n3']**2)/2*math.sqrt((params['r_naruzhnyj_radius_m_n3']+params['r_vnutrennij_radius_m_n3'])/(params['r_naruzhnyj_radius_m_n3']-params['r_vnutrennij_radius_m_n3'])))))

def calc_lws_n3(params):
    """
    Excel M355 / O355
    Формула (Excel): =IF(O354="","",10*LOG10(O354/(10^(-12))))
    """
    return (((None) if (params['ws_moschnost_shuma_na_vyhode_kanala_vt_n3']==None) else (10*math.log10(params['ws_moschnost_shuma_na_vyhode_kanala_vt_n3']/(10**(-12))))))

def calc_r_vnutrennij_radius_m_n4(params):
    """
    Excel M356 / O356
    Формула (Excel): =IF(AND(E42=0,E41<=3),"",IF(AND(E42=0,E41>=4),O342+E49*0.001,IF(AND(E42>0,E41<=2),"",IF(AND(E42>0,E41>=2),O342+E47*0.001))))
    """
    return (((None) if ((params['r1_vnutrennij_radius_1_kassety_mm']==0 and params['kolichestvo_kasset']<=3)) else (((params['r_naruzhnyj_radius_m_n3']+params['e49']*0.001) if ((params['r1_vnutrennij_radius_1_kassety_mm']==0 and params['kolichestvo_kasset']>=4)) else (((None) if ((params['r1_vnutrennij_radius_1_kassety_mm']>0 and params['kolichestvo_kasset']<=2)) else (((params['r_naruzhnyj_radius_m_n3']+params['t3_tolschina_oblicovki_mm']*0.001) if ((params['r1_vnutrennij_radius_1_kassety_mm']>0 and params['kolichestvo_kasset']>=2)) else (None)))))))))

def calc_r_naruzhnyj_radius_m_n4(params):
    """
    Excel M357 / O357
    Формула (Excel): =IF(AND(E42=0,E41<=3),"",IF(AND(E42=0,E41>=4),O356+E50*0.001,IF(AND(E42>0,E41<=2),"",IF(AND(E42>0,E41>=3),O356+E48*0.001))))
    """
    return (((None) if ((params['r1_vnutrennij_radius_1_kassety_mm']==0 and params['kolichestvo_kasset']<=3)) else (((params['r_vnutrennij_radius_m_n4']+params['e50']*0.001) if ((params['r1_vnutrennij_radius_1_kassety_mm']==0 and params['kolichestvo_kasset']>=4)) else (((None) if ((params['r1_vnutrennij_radius_1_kassety_mm']>0 and params['kolichestvo_kasset']<=2)) else (((params['r_vnutrennij_radius_m_n4']+params['e48']*0.001) if ((params['r1_vnutrennij_radius_1_kassety_mm']>0 and params['kolichestvo_kasset']>=3)) else (None)))))))))

def calc_dh_gidravlicheskij_diametr_m_n4(params):
    """
    Excel M358 / O358
    Формула (Excel): =IF(AND(O356="",O357=""),"",2*(O357-O356))
    """
    return (((None) if ((params['r_vnutrennij_radius_m_n4']==None and params['r_naruzhnyj_radius_m_n4']==None)) else (2*(params['r_naruzhnyj_radius_m_n4']-params['r_vnutrennij_radius_m_n4']))))

def calc_d_shirina_kanala_m_n4(params):
    """
    Excel M359 / O359
    Формула (Excel): =IF(AND(O356="",O357=""),"",O357-O356)
    """
    return (((None) if ((params['r_vnutrennij_radius_m_n4']==None and params['r_naruzhnyj_radius_m_n4']==None)) else (params['r_naruzhnyj_radius_m_n4']-params['r_vnutrennij_radius_m_n4'])))

def calc_f_ploschad_kanala_m2_n4(params):
    """
    Excel M360 / O360
    Формула (Excel): =IF(AND(O356="",O357=""),"",PI()*(O357^2-O356^2))
    """
    return (((None) if ((params['r_vnutrennij_radius_m_n4']==None and params['r_naruzhnyj_radius_m_n4']==None)) else (math.pi*(params['r_naruzhnyj_radius_m_n4']**2-params['r_vnutrennij_radius_m_n4']**2))))

def calc_f_dh_0_5_n4(params):
    """
    Excel M361 / O361
    Формула (Excel): =IF(O358="","",O360*SQRT(O358))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n4']==None) else (params['f_ploschad_kanala_m2_n4']*math.sqrt(params['dh_gidravlicheskij_diametr_m_n4']))))

def calc_h_srednyaya_tolschina_plastin_m_n4(params):
    """
    Excel M362 / O362
    Формула (Excel): =IF(O359="","",IF(E42=0,(O356*E49*0.001+O357*E51*0.001)/(O356+O357),(O356*E47*0.001+O357*E49*0.001)/(O356+O357)))
    """
    return (((None) if (params['d_shirina_kanala_m_n4']==None) else ((((params['r_vnutrennij_radius_m_n4']*params['e49']*0.001+params['r_naruzhnyj_radius_m_n4']*params['e51']*0.001)/(params['r_vnutrennij_radius_m_n4']+params['r_naruzhnyj_radius_m_n4'])) if (params['r1_vnutrennij_radius_1_kassety_mm']==0) else ((params['r_vnutrennij_radius_m_n4']*params['t3_tolschina_oblicovki_mm']*0.001+params['r_naruzhnyj_radius_m_n4']*params['e49']*0.001)/(params['r_vnutrennij_radius_m_n4']+params['r_naruzhnyj_radius_m_n4']))))))

def calc_pd_skorostnoj_napor_na_vyhode_pa_n4(params):
    """
    Excel M363 / O363
    Формула (Excel): =IF(O358="","",$O$257^2*O358*$O$254*$O$256/(2*$O$259*$O$261^2))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n4']==None) else (params['g_rashod_sredy_kg_s']**2*params['dh_gidravlicheskij_diametr_m_n4']*params['r_gazovaya_postoyannaya_m2s2_k']*params['t_absolyutnaya_temperatura_pered_glushitelem_k']/(2*params['pat_atmosfernoe_davlenie_pa']*params['summ_diam']**2))))

def calc_g_rashod_v_kanale_kg_s_n4(params):
    """
    Excel M364 / O364
    Формула (Excel): =IF(O358="","",(O257*O360*SQRT(O358))/summ_diam)
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n4']==None) else ((params['g_rashod_sredy_kg_s']*params['f_ploschad_kanala_m2_n4']*math.sqrt(params['dh_gidravlicheskij_diametr_m_n4']))/params['summ_diam'])))

def calc_w_skorost_v_kanale_m_s_n4(params):
    """
    Excel M365 / O365
    Формула (Excel): =IF(O358="","",(O364*$O$254*$O$256)/($O$259*O360))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n4']==None) else ((params['g_rashod_v_kanale_kg_s_n4']*params['r_gazovaya_postoyannaya_m2s2_k']*params['t_absolyutnaya_temperatura_pered_glushitelem_k'])/(params['pat_atmosfernoe_davlenie_pa']*params['f_ploschad_kanala_m2_n4']))))

def calc_m_chislo_maha_v_kanale_n4(params):
    """
    Excel M366 / O366
    Формула (Excel): =IF(O358="","",O365/SQRT($O$255*$O$254*$O$256))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n4']==None) else (params['w_skorost_v_kanale_m_s_n4']/math.sqrt(params['k_pokazatel_adiabaty']*params['r_gazovaya_postoyannaya_m2s2_k']*params['t_absolyutnaya_temperatura_pered_glushitelem_k']))))

def calc_k_m_n4(params):
    """
    Excel M367 / O367
    Формула (Excel): =IF(O366="","",IF(O366<=SQRT(0.8),8*10^(-5)*O366^3,IF(AND(O366>SQRT(0.8),O366<=20^0.2),10^(-4)*O366^5,IF(O366>20^0.2,2*10^(-3)))))
    """
    return (((None) if (params['m_chislo_maha_v_kanale_n4']==None) else (((8*10**(-5)*params['m_chislo_maha_v_kanale_n4']**3) if (params['m_chislo_maha_v_kanale_n4']<=math.sqrt(0.8)) else (((10**(-4)*params['m_chislo_maha_v_kanale_n4']**5) if ((params['m_chislo_maha_v_kanale_n4']>math.sqrt(0.8) and params['m_chislo_maha_v_kanale_n4']<=20**0.2)) else (((2*10**(-3)) if (params['m_chislo_maha_v_kanale_n4']>20**0.2) else (None)))))))))

def calc_ds_n4(params):
    """
    Excel M368 / O368
    Формула (Excel): =IF(O359="","",MIN(O359,O362))
    """
    return (((None) if (params['d_shirina_kanala_m_n4']==None) else (min(params['d_shirina_kanala_m_n4'], params['h_srednyaya_tolschina_plastin_m_n4']))))

def calc_ws_moschnost_shuma_na_vyhode_kanala_vt_n4(params):
    """
    Excel M369 / O369
    Формула (Excel): =IF(O364="","",O367*O364*(O365^2)/2*SQRT((O357+O356)/(O357-O356)))
    """
    return (((None) if (params['g_rashod_v_kanale_kg_s_n4']==None) else (params['k_m_n4']*params['g_rashod_v_kanale_kg_s_n4']*(params['w_skorost_v_kanale_m_s_n4']**2)/2*math.sqrt((params['r_naruzhnyj_radius_m_n4']+params['r_vnutrennij_radius_m_n4'])/(params['r_naruzhnyj_radius_m_n4']-params['r_vnutrennij_radius_m_n4'])))))

def calc_lws_n4(params):
    """
    Excel M370 / O370
    Формула (Excel): =IF(O369="","",10*LOG10(O369/(10^(-12))))
    """
    return (((None) if (params['ws_moschnost_shuma_na_vyhode_kanala_vt_n4']==None) else (10*math.log10(params['ws_moschnost_shuma_na_vyhode_kanala_vt_n4']/(10**(-12))))))

def calc_r_vnutrennij_radius_m_n5(params):
    """
    Excel M371 / O371
    Формула (Excel): =IF(AND(E42=0,E41<=4),"",IF(AND(E42=0,E41>=5),O357+E51*0.001,IF(AND(E42>0,E41<=3),"",IF(AND(E42>0,E41>=4),O357+E49*0.001))))
    """
    return (((None) if ((params['r1_vnutrennij_radius_1_kassety_mm']==0 and params['kolichestvo_kasset']<=4)) else (((params['r_naruzhnyj_radius_m_n4']+params['e51']*0.001) if ((params['r1_vnutrennij_radius_1_kassety_mm']==0 and params['kolichestvo_kasset']>=5)) else (((None) if ((params['r1_vnutrennij_radius_1_kassety_mm']>0 and params['kolichestvo_kasset']<=3)) else (((params['r_naruzhnyj_radius_m_n4']+params['e49']*0.001) if ((params['r1_vnutrennij_radius_1_kassety_mm']>0 and params['kolichestvo_kasset']>=4)) else (None)))))))))

def calc_r_naruzhnyj_radius_m_n5(params):
    """
    Excel M372 / O372
    Формула (Excel): =IF(AND(E42=0,E41<=4),"",IF(AND(E42=0,E41>4),O371+E52*0.001,IF(AND(E42>0,E41<=3),"",IF(AND(E42>0,E41>=4),O371+E50*0.001))))
    """
    return (((None) if ((params['r1_vnutrennij_radius_1_kassety_mm']==0 and params['kolichestvo_kasset']<=4)) else (((params['r_vnutrennij_radius_m_n5']+params['e52']*0.001) if ((params['r1_vnutrennij_radius_1_kassety_mm']==0 and params['kolichestvo_kasset']>4)) else (((None) if ((params['r1_vnutrennij_radius_1_kassety_mm']>0 and params['kolichestvo_kasset']<=3)) else (((params['r_vnutrennij_radius_m_n5']+params['e50']*0.001) if ((params['r1_vnutrennij_radius_1_kassety_mm']>0 and params['kolichestvo_kasset']>=4)) else (None)))))))))

def calc_dh_gidravlicheskij_diametr_m_n5(params):
    """
    Excel M373 / O373
    Формула (Excel): =IF(AND(O371="",O372=""),"",2*(O372-O371))
    """
    return (((None) if ((params['r_vnutrennij_radius_m_n5']==None and params['r_naruzhnyj_radius_m_n5']==None)) else (2*(params['r_naruzhnyj_radius_m_n5']-params['r_vnutrennij_radius_m_n5']))))

def calc_d_shirina_kanala_m_n5(params):
    """
    Excel M374 / O374
    Формула (Excel): =IF(AND(O371="",O372=""),"",O372-O371)
    """
    return (((None) if ((params['r_vnutrennij_radius_m_n5']==None and params['r_naruzhnyj_radius_m_n5']==None)) else (params['r_naruzhnyj_radius_m_n5']-params['r_vnutrennij_radius_m_n5'])))

def calc_f_ploschad_kanala_m2_n5(params):
    """
    Excel M375 / O375
    Формула (Excel): =IF(AND(O371="",O372=""),"",PI()*(O372^2-O371^2))
    """
    return (((None) if ((params['r_vnutrennij_radius_m_n5']==None and params['r_naruzhnyj_radius_m_n5']==None)) else (math.pi*(params['r_naruzhnyj_radius_m_n5']**2-params['r_vnutrennij_radius_m_n5']**2))))

def calc_f_dh_0_5_n5(params):
    """
    Excel M376 / O376
    Формула (Excel): =IF(O373="","",O375*SQRT(O373))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n5']==None) else (params['f_ploschad_kanala_m2_n5']*math.sqrt(params['dh_gidravlicheskij_diametr_m_n5']))))

def calc_h_srednyaya_tolschina_plastin_m_n5(params):
    """
    Excel M377 / O377
    Формула (Excel): =IF(O374="","",IF(E42=0,(O371*E51*0.001+O372*E53*0.001)/(O371+O372),(O371*E49*0.001+O372*E51*0.001)/(O371+O372)))
    """
    return (((None) if (params['d_shirina_kanala_m_n5']==None) else ((((params['r_vnutrennij_radius_m_n5']*params['e51']*0.001+params['r_naruzhnyj_radius_m_n5']*params['e53']*0.001)/(params['r_vnutrennij_radius_m_n5']+params['r_naruzhnyj_radius_m_n5'])) if (params['r1_vnutrennij_radius_1_kassety_mm']==0) else ((params['r_vnutrennij_radius_m_n5']*params['e49']*0.001+params['r_naruzhnyj_radius_m_n5']*params['e51']*0.001)/(params['r_vnutrennij_radius_m_n5']+params['r_naruzhnyj_radius_m_n5']))))))

def calc_pd_skorostnoj_napor_na_vyhode_pa_n5(params):
    """
    Excel M378 / O378
    Формула (Excel): =IF(O373="","",$O$257^2*O373*$O$254*$O$256/(2*$O$259*$O$261^2))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n5']==None) else (params['g_rashod_sredy_kg_s']**2*params['dh_gidravlicheskij_diametr_m_n5']*params['r_gazovaya_postoyannaya_m2s2_k']*params['t_absolyutnaya_temperatura_pered_glushitelem_k']/(2*params['pat_atmosfernoe_davlenie_pa']*params['summ_diam']**2))))

def calc_g_rashod_v_kanale_kg_s_n5(params):
    """
    Excel M379 / O379
    Формула (Excel): =IF(O373="","",($O$257*O375*SQRT(O373))/$O$261)
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n5']==None) else ((params['g_rashod_sredy_kg_s']*params['f_ploschad_kanala_m2_n5']*math.sqrt(params['dh_gidravlicheskij_diametr_m_n5']))/params['summ_diam'])))

def calc_w_skorost_v_kanale_m_s_n5(params):
    """
    Excel M380 / O380
    Формула (Excel): =IF(O373="","",(O379*$O$254*$O$256)/($O$259*O375))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n5']==None) else ((params['g_rashod_v_kanale_kg_s_n5']*params['r_gazovaya_postoyannaya_m2s2_k']*params['t_absolyutnaya_temperatura_pered_glushitelem_k'])/(params['pat_atmosfernoe_davlenie_pa']*params['f_ploschad_kanala_m2_n5']))))

def calc_m_chislo_maha_v_kanale_n5(params):
    """
    Excel M381 / O381
    Формула (Excel): =IF(O373="","",O380/SQRT($O$255*$O$254*$O$256))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n5']==None) else (params['w_skorost_v_kanale_m_s_n5']/math.sqrt(params['k_pokazatel_adiabaty']*params['r_gazovaya_postoyannaya_m2s2_k']*params['t_absolyutnaya_temperatura_pered_glushitelem_k']))))

def calc_k_m_n5(params):
    """
    Excel M382 / O382
    Формула (Excel): =IF(O381="","",IF(O381<=SQRT(0.8),8*10^(-5)*O381^3,IF(AND(O381>SQRT(0.8),O381<=20^0.2),10^(-4)*O381^5,IF(O381>20^0.2,2*10^(-3)))))
    """
    return (((None) if (params['m_chislo_maha_v_kanale_n5']==None) else (((8*10**(-5)*params['m_chislo_maha_v_kanale_n5']**3) if (params['m_chislo_maha_v_kanale_n5']<=math.sqrt(0.8)) else (((10**(-4)*params['m_chislo_maha_v_kanale_n5']**5) if ((params['m_chislo_maha_v_kanale_n5']>math.sqrt(0.8) and params['m_chislo_maha_v_kanale_n5']<=20**0.2)) else (((2*10**(-3)) if (params['m_chislo_maha_v_kanale_n5']>20**0.2) else (None)))))))))

def calc_ds_n5(params):
    """
    Excel M383 / O383
    Формула (Excel): =IF(O374="","",MIN(O374,O377))
    """
    return (((None) if (params['d_shirina_kanala_m_n5']==None) else (min(params['d_shirina_kanala_m_n5'], params['h_srednyaya_tolschina_plastin_m_n5']))))

def calc_ws_moschnost_shuma_na_vyhode_kanala_vt_n5(params):
    """
    Excel M384 / O384
    Формула (Excel): =IF(O379="","",O382*O379*(O380^2)/2*SQRT((O372+O371)/(O372-O371)))
    """
    return (((None) if (params['g_rashod_v_kanale_kg_s_n5']==None) else (params['k_m_n5']*params['g_rashod_v_kanale_kg_s_n5']*(params['w_skorost_v_kanale_m_s_n5']**2)/2*math.sqrt((params['r_naruzhnyj_radius_m_n5']+params['r_vnutrennij_radius_m_n5'])/(params['r_naruzhnyj_radius_m_n5']-params['r_vnutrennij_radius_m_n5'])))))

def calc_lws_n5(params):
    """
    Excel M385 / O385
    Формула (Excel): =IF(O384="","",10*LOG10(O384/(10^(-12))))
    """
    return (((None) if (params['ws_moschnost_shuma_na_vyhode_kanala_vt_n5']==None) else (10*math.log10(params['ws_moschnost_shuma_na_vyhode_kanala_vt_n5']/(10**(-12))))))

def calc_r_vnutrennij_radius_m_n6(params):
    """
    Excel M386 / O386
    Формула (Excel): =IF(E42=0,"",IF(AND(E42>0,E41<=4),"",IF(AND(E42>0,E41>=5),O372+E51*0.001)))
    """
    return (((None) if (params['r1_vnutrennij_radius_1_kassety_mm']==0) else (((None) if ((params['r1_vnutrennij_radius_1_kassety_mm']>0 and params['kolichestvo_kasset']<=4)) else (((params['r_naruzhnyj_radius_m_n5']+params['e51']*0.001) if ((params['r1_vnutrennij_radius_1_kassety_mm']>0 and params['kolichestvo_kasset']>=5)) else (None)))))))

def calc_r_naruzhnyj_radius_m_n6(params):
    """
    Excel M387 / O387
    Формула (Excel): =IF(E42=0,"",IF(AND(E42>0,E41<=4),"",IF(AND(E42>0,E41>=5),O386+E52*0.001)))
    """
    return (((None) if (params['r1_vnutrennij_radius_1_kassety_mm']==0) else (((None) if ((params['r1_vnutrennij_radius_1_kassety_mm']>0 and params['kolichestvo_kasset']<=4)) else (((params['r_vnutrennij_radius_m_n6']+params['e52']*0.001) if ((params['r1_vnutrennij_radius_1_kassety_mm']>0 and params['kolichestvo_kasset']>=5)) else (None)))))))

def calc_dh_gidravlicheskij_diametr_m_n6(params):
    """
    Excel M388 / O388
    Формула (Excel): =IF(AND(O386="",O387=""),"",2*(O387-O386))
    """
    return (((None) if ((params['r_vnutrennij_radius_m_n6']==None and params['r_naruzhnyj_radius_m_n6']==None)) else (2*(params['r_naruzhnyj_radius_m_n6']-params['r_vnutrennij_radius_m_n6']))))

def calc_d_shirina_kanala_m_n6(params):
    """
    Excel M389 / O389
    Формула (Excel): =IF(AND(O386="",O387=""),"",O387-O386)
    """
    return (((None) if ((params['r_vnutrennij_radius_m_n6']==None and params['r_naruzhnyj_radius_m_n6']==None)) else (params['r_naruzhnyj_radius_m_n6']-params['r_vnutrennij_radius_m_n6'])))

def calc_f_ploschad_kanala_m2_n6(params):
    """
    Excel M390 / O390
    Формула (Excel): =IF(AND(O386="",O387=""),"",PI()*(O387^2-O386^2))
    """
    return (((None) if ((params['r_vnutrennij_radius_m_n6']==None and params['r_naruzhnyj_radius_m_n6']==None)) else (math.pi*(params['r_naruzhnyj_radius_m_n6']**2-params['r_vnutrennij_radius_m_n6']**2))))

def calc_f_dh_0_5_n6(params):
    """
    Excel M391 / O391
    Формула (Excel): =IF(O388="","",O390*SQRT(O388))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n6']==None) else (params['f_ploschad_kanala_m2_n6']*math.sqrt(params['dh_gidravlicheskij_diametr_m_n6']))))

def calc_h_srednyaya_tolschina_plastin_m_n6(params):
    """
    Excel M392 / O392
    Формула (Excel): =IF(O389="","",IF(E42>0,(O386*E51*0.001+O387*E53*0.001)/(O386+O387)))
    """
    return (((None) if (params['d_shirina_kanala_m_n6']==None) else ((((params['r_vnutrennij_radius_m_n6']*params['e51']*0.001+params['r_naruzhnyj_radius_m_n6']*params['e53']*0.001)/(params['r_vnutrennij_radius_m_n6']+params['r_naruzhnyj_radius_m_n6'])) if (params['r1_vnutrennij_radius_1_kassety_mm']>0) else (None)))))

def calc_pd_skorostnoj_napor_na_vyhode_pa_n6(params):
    """
    Excel M393 / O393
    Формула (Excel): =IF(O388="","",$O$257^2*O388*$O$254*$O$256/(2*$O$259*$O$261^2))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n6']==None) else (params['g_rashod_sredy_kg_s']**2*params['dh_gidravlicheskij_diametr_m_n6']*params['r_gazovaya_postoyannaya_m2s2_k']*params['t_absolyutnaya_temperatura_pered_glushitelem_k']/(2*params['pat_atmosfernoe_davlenie_pa']*params['summ_diam']**2))))

def calc_g_rashod_v_kanale_kg_s_n6(params):
    """
    Excel M394 / O394
    Формула (Excel): =IF(O388="","",($O$257*O390*SQRT(O388))/$O$261)
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n6']==None) else ((params['g_rashod_sredy_kg_s']*params['f_ploschad_kanala_m2_n6']*math.sqrt(params['dh_gidravlicheskij_diametr_m_n6']))/params['summ_diam'])))

def calc_w_skorost_v_kanale_m_s_n6(params):
    """
    Excel M395 / O395
    Формула (Excel): =IF(O388="","",(O394*$O$254*$O$256)/($O$259*O390))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n6']==None) else ((params['g_rashod_v_kanale_kg_s_n6']*params['r_gazovaya_postoyannaya_m2s2_k']*params['t_absolyutnaya_temperatura_pered_glushitelem_k'])/(params['pat_atmosfernoe_davlenie_pa']*params['f_ploschad_kanala_m2_n6']))))

def calc_m_chislo_maha_v_kanale_n6(params):
    """
    Excel M396 / O396
    Формула (Excel): =IF(O388="","",O395/SQRT($O$255*$O$254*$O$256))
    """
    return (((None) if (params['dh_gidravlicheskij_diametr_m_n6']==None) else (params['w_skorost_v_kanale_m_s_n6']/math.sqrt(params['k_pokazatel_adiabaty']*params['r_gazovaya_postoyannaya_m2s2_k']*params['t_absolyutnaya_temperatura_pered_glushitelem_k']))))

def calc_k_m_n6(params):
    """
    Excel M397 / O397
    Формула (Excel): =IF(O396="","",IF(O396<=SQRT(0.8),8*10^(-5)*O396^3,IF(AND(O396>SQRT(0.8),O396<=20^0.2),10^(-4)*O396^5,IF(O396>20^0.2,2*10^(-3)))))
    """
    return (((None) if (params['m_chislo_maha_v_kanale_n6']==None) else (((8*10**(-5)*params['m_chislo_maha_v_kanale_n6']**3) if (params['m_chislo_maha_v_kanale_n6']<=math.sqrt(0.8)) else (((10**(-4)*params['m_chislo_maha_v_kanale_n6']**5) if ((params['m_chislo_maha_v_kanale_n6']>math.sqrt(0.8) and params['m_chislo_maha_v_kanale_n6']<=20**0.2)) else (((2*10**(-3)) if (params['m_chislo_maha_v_kanale_n6']>20**0.2) else (None)))))))))

def calc_ds_n6(params):
    """
    Excel M398 / O398
    Формула (Excel): =IF(O389="","",MIN(O389,O392))
    """
    return (((None) if (params['d_shirina_kanala_m_n6']==None) else (min(params['d_shirina_kanala_m_n6'], params['h_srednyaya_tolschina_plastin_m_n6']))))

def calc_ws_moschnost_shuma_na_vyhode_kanala_vt_n6(params):
    """
    Excel M399 / O399
    Формула (Excel): =IF(O394="","",O397*O394*(O395^2)/2*SQRT((O387+O386)/(O387-O386)))
    """
    return (((None) if (params['g_rashod_v_kanale_kg_s_n6']==None) else (params['k_m_n6']*params['g_rashod_v_kanale_kg_s_n6']*(params['w_skorost_v_kanale_m_s_n6']**2)/2*math.sqrt((params['r_naruzhnyj_radius_m_n6']+params['r_vnutrennij_radius_m_n6'])/(params['r_naruzhnyj_radius_m_n6']-params['r_vnutrennij_radius_m_n6'])))))

def calc_lws_n6(params):
    """
    Excel M400 / O400
    Формула (Excel): =IF(O399="","",10*LOG10(O399/(10^(-12))))
    """
    return (((None) if (params['ws_moschnost_shuma_na_vyhode_kanala_vt_n6']==None) else (10*math.log10(params['ws_moschnost_shuma_na_vyhode_kanala_vt_n6']/(10**(-12))))))




def calc_plotnost_rho_po_idealnomu_gazu(params):
    """
    Плотность ρ по уравнению идеального газа
    Excel M270 / O270
    ρ = p / (R·T)
    """
    p_total = params["ptr_pa"]
    R = params["r_gazovaya_postoyannaya_m2s2_k"]
    T = params["t_absolyutnaya_temperatura_pered_glushitelem_k"]
    return p_total / (R * T)



def calc_stupeni_n0(params):
    """
    Расчет параметра ступени N0
    Excel: формула для начальной ступени
    Excel M173 / O173
    """
    # 🔴 Заглушка: формулу нужно уточнить из Excel
    return 0


def calc_y_n0(params):
    """
    Коэффициент y для ступени N0
    Excel: формула для начальной ступени
    Excel M175 / O175
    """
    return 0


def calc_perepad_davlenij_n0(params):
    """
    Перепад давлений для ступени N0
    Excel: формула для начальной ступени
    Excel M176 / O176
    """
    return 0


def calc_n0(params):
    """
    Общая величина N0
    Excel: базовое значение
    Excel M177 / O177
    """
    return 0


def calc_n0_2(params):
    """
    Вспомогательный расчет для N0 (2)
    Excel M178 / O178
    """
    return 0


def calc_n0_3(params):
    """
    Вспомогательный расчет для N0 (3)
    Excel M179 / O179
    """
    return 0


def calc_udelnyj_obem_m3_kg_out(params):
    """ трансляция из таблицы инпут"""
    return params["udelnyj_obem_m3_kg"]
def calc_massovyj_rashod_kg_s_out(params):
    """ трансляция из таблицы инпут"""
    return params["massovyj_rashod_kg_s"]
def calc_diametr_shg_m_out(params):
    """ трансляция из таблицы инпут"""
    return params["diametr_shg_m"]
def calc_koefficient_treniya_out(params):
    """ трансляция из таблицы инпут"""
    return params["koefficient_treniya"]
def calc_atmosfernoe_davlenie_pa_out(params):
    """ трансляция из таблицы инпут"""
    return params["atmosfernoe_davlenie_pa"]



CALC_FUNCTIONS = OrderedDict([("edinica_rashoda_imya", {"fnc": calc_edinica_rashoda_imya, "cell": "Excel O5"}),
("ploschad_vyhoda_shg_m2", {"fnc": calc_ploschad_vyhoda_shg_m2, "cell": "Excel O18"}),
("sreda_2", {"fnc": calc_sreda_2, "cell": "Excel O23"}),
("rashod_sredy_g_kg_s", {"fnc": calc_rashod_sredy_g_kg_s, "cell": "Excel O24"}),
("temperatura_sredy_s_2", {"fnc": calc_temperatura_sredy_s_2, "cell": "Excel O25"}),
("davlenie_na_vhode_v_shg_pi_abs_mpa", {"fnc": calc_davlenie_na_vhode_v_shg_pi_abs_mpa, "cell": "Excel O26"}),
("gazovaya_postoyannaya_m2_s2_k", {"fnc": calc_gazovaya_postoyannaya_m2_s2_k, "cell": "Excel O29"}),
("koeffcient_adiabaty", {"fnc": calc_koeffcient_adiabaty, "cell": "Excel O31"}),
("kolichestvo_stupenej_drosselirovaniya_j", {"fnc": calc_kolichestvo_stupenej_drosselirovaniya_j, "cell": "Excel O34"}),
("maksimalnoe_kolichestvo_otverstij_kmah_v_drosselnoj_reshetke_sht", {"fnc": calc_maksimalnoe_kolichestvo_otverstij_kmah_v_drosselnoj_reshetke_sht, "cell": "Excel O35"}),
("stupeni_n1", {"fnc": calc_stupeni_n1, "cell": "Excel O45"}),
("stupeni_n2", {"fnc": calc_stupeni_n2, "cell": "Excel O49"}),
("stupeni_n3", {"fnc": calc_stupeni_n3, "cell": "Excel O53"}),
("stupeni_n4", {"fnc": calc_stupeni_n4, "cell": "Excel O57"}),
("stupeni_n5", {"fnc": calc_stupeni_n5, "cell": "Excel O61"}),
("stupeni_n6", {"fnc": calc_stupeni_n6, "cell": "Excel O65"}),
("stupeni_n7", {"fnc": calc_stupeni_n7, "cell": "Excel O69"}),
("stupeni_n8", {"fnc": calc_stupeni_n8, "cell": "Excel O73"}),
("stupeni_n9", {"fnc": calc_stupeni_n9, "cell": "Excel O77"}),
("stupeni_n10", {"fnc": calc_stupeni_n10, "cell": "Excel O81"}),
("stupenin1_2_n1", {"fnc": calc_stupenin1_2_n1, "cell": "Excel O90"}),
("perimetr_m", {"fnc": calc_perimetr_m, "cell": "Excel O137"}),
("sk_ploschad_vyhodnogo_secheniya_korpusa_do_kryshki_kv_m", {"fnc": calc_sk_ploschad_vyhodnogo_secheniya_korpusa_do_kryshki_kv_m, "cell": "Excel O138"}),
("da_vnutrennij_diametr_vyhlopa_iz_korpusa_m", {"fnc": calc_da_vnutrennij_diametr_vyhlopa_iz_korpusa_m, "cell": "Excel O139"}),
("stupeni_n1_3", {"fnc": calc_stupeni_n1_3, "cell": "Excel O180"}),
("stupeni_n4_3", {"fnc": calc_stupeni_n4_3, "cell": "Excel O201"}),
("stupeni_n5_3", {"fnc": calc_stupeni_n5_3, "cell": "Excel O208"}),
("stupeni_n6_3", {"fnc": calc_stupeni_n6_3, "cell": "Excel O215"}),
("stupeni_n7_3", {"fnc": calc_stupeni_n7_3, "cell": "Excel O222"}),
("stupeni_n8_3", {"fnc": calc_stupeni_n8_3, "cell": "Excel O229"}),
("stupeni_n9_3", {"fnc": calc_stupeni_n9_3, "cell": "Excel O236"}),
("stupeni_n10_3", {"fnc": calc_stupeni_n10_3, "cell": "Excel O243"}),
("obtekateli", {"fnc": calc_obtekateli, "cell": "Excel O253"}),
("d_vnutrennij_diametr_shg_m", {"fnc": calc_d_vnutrennij_diametr_shg_m, "cell": "Excel O258"}),
("pat_atmosfernoe_davlenie_pa", {"fnc": calc_pat_atmosfernoe_davlenie_pa, "cell": "Excel O259"}),
("l_dlina_kanalov_m", {"fnc": calc_l_dlina_kanalov_m, "cell": "Excel O263"}),
("pat_atmosfernoe_davlenie_pa_2", {"fnc": calc_pat_atmosfernoe_davlenie_pa_2, "cell": "Excel O278"}),
("d_vnutrennij_diametr_korpusa_stupeni_zvukopogloscheniya_m", {"fnc": calc_d_vnutrennij_diametr_korpusa_stupeni_zvukopogloscheniya_m, "cell": "Excel O279"}),
("hk_osevoe_rasstoyanie_ot_vyhodnogo_secheniya_korpusa_do_kryshki_m", {"fnc": calc_hk_osevoe_rasstoyanie_ot_vyhodnogo_secheniya_korpusa_do_kryshki_m, "cell": "Excel O281"}),
("r_vnutrennij_radius_m_n1", {"fnc": calc_r_vnutrennij_radius_m_n1, "cell": "Excel O311"}),
("stupeni_n0", {"fnc": calc_stupeni_n0, "cell": "Excel O173"}),
("y_n0", {"fnc": calc_y_n0, "cell": "Excel O175"}),
("perepad_davlenij_n0", {"fnc": calc_perepad_davlenij_n0, "cell": "Excel O176"}),
("n0", {"fnc": calc_n0, "cell": "Excel O177"}),
("n0_2", {"fnc": calc_n0_2, "cell": "Excel O178"}),
("n0_3", {"fnc": calc_n0_3, "cell": "Excel O179"}),
("skorost_na_vyhode_shg_m_s", {"fnc": calc_skorost_na_vyhode_shg_m_s, "cell": "Excel O19"}),
("g_rashod_sredy_kg_s", {"fnc": calc_g_rashod_sredy_kg_s, "cell": "Excel O257"}),
("g_rashod_sredy_kg_s_2", {"fnc": calc_g_rashod_sredy_kg_s_2, "cell": "Excel O274"}),
("temperatura_k", {"fnc": calc_temperatura_k, "cell": "Excel O135"}),
("molyarnaya_massa_sredy_kg_mol", {"fnc": calc_molyarnaya_massa_sredy_kg_mol, "cell": "Excel O6"}),
("r_gazovaya_postoyannaya_m2s2_k", {"fnc": calc_r_gazovaya_postoyannaya_m2s2_k, "cell": "Excel O254"}),
("r_individualnaya_gazovaya_postoyannaya_m2s2_k", {"fnc": calc_r_individualnaya_gazovaya_postoyannaya_m2s2_k, "cell": "Excel O276"}),
("epsilon_1", {"fnc": calc_epsilon_1, "cell": "Excel O12"}),
("y_1", {"fnc": calc_y_1, "cell": "Excel O14"}),
("kriticheskaya_skorost_skr_m_s", {"fnc": calc_kriticheskaya_skorost_skr_m_s, "cell": "Excel O28"}),
("kriticheskij_perepad_davlenij", {"fnc": calc_kriticheskij_perepad_davlenij, "cell": "Excel O144"}),
("k_pokazatel_adiabaty", {"fnc": calc_k_pokazatel_adiabaty, "cell": "Excel O255"}),
("k_koefficient_adiabaty", {"fnc": calc_k_koefficient_adiabaty, "cell": "Excel O275"}),
("stupenin1_2_n2", {"fnc": calc_stupenin1_2_n2, "cell": "Excel O94"}),
("stupenin1_2_n3", {"fnc": calc_stupenin1_2_n3, "cell": "Excel O98"}),
("stupenin1_2_n4", {"fnc": calc_stupenin1_2_n4, "cell": "Excel O102"}),
("stupenin1_2_n5", {"fnc": calc_stupenin1_2_n5, "cell": "Excel O106"}),
("stupenin1_2_n6", {"fnc": calc_stupenin1_2_n6, "cell": "Excel O110"}),
("stupenin1_2_n7", {"fnc": calc_stupenin1_2_n7, "cell": "Excel O114"}),
("stupenin1_2_n8", {"fnc": calc_stupenin1_2_n8, "cell": "Excel O118"}),
("stupenin1_2_n9", {"fnc": calc_stupenin1_2_n9, "cell": "Excel O122"}),
("stupenin1_2_n10", {"fnc": calc_stupenin1_2_n10, "cell": "Excel O126"}),
("stupeni_n2_3", {"fnc": calc_stupeni_n2_3, "cell": "Excel O187"}),
("stupeni_n3_3", {"fnc": calc_stupeni_n3_3, "cell": "Excel O194"}),
("sa_ploschad_secheniya_shumoglushitelya_m2", {"fnc": calc_sa_ploschad_secheniya_shumoglushitelya_m2, "cell": "Excel O136"}),
("da_vnutrennij_diametr_vyhlopa_m", {"fnc": calc_da_vnutrennij_diametr_vyhlopa_m, "cell": "Excel O280"}),
("sk_ploschad_vyhodnogo_secheniya_kanala_korpusa_do_kryshki_m2", {"fnc": calc_sk_ploschad_vyhodnogo_secheniya_kanala_korpusa_do_kryshki_m2, "cell": "Excel O282"}),
("r_naruzhnyj_radius_m_n1", {"fnc": calc_r_naruzhnyj_radius_m_n1, "cell": "Excel O312"}),
("r_reaktivnye_sily_n", {"fnc": calc_r_reaktivnye_sily_n, "cell": "Excel O20"}),
("t_absolyutnaya_temperatura_pered_glushitelem_k", {"fnc": calc_t_absolyutnaya_temperatura_pered_glushitelem_k, "cell": "Excel O256"}),
("t_temperatura_sredy_k", {"fnc": calc_t_temperatura_sredy_k, "cell": "Excel O277"}),
("plotnost_sredy_kg_m3", {"fnc": calc_plotnost_sredy_kg_m3, "cell": "Excel O7"}),
("nezapolnennaya_ploschad_kv_m", {"fnc": calc_nezapolnennaya_ploschad_kv_m, "cell": "Excel O140"}),
("sa", {"fnc": calc_sa, "cell": "Excel O283"}),
("dh_gidravlicheskij_diametr_m_n1", {"fnc": calc_dh_gidravlicheskij_diametr_m_n1, "cell": "Excel O313"}),
("d_shirina_kanala_m_n1", {"fnc": calc_d_shirina_kanala_m_n1, "cell": "Excel O314"}),
("f_ploschad_kanala_m2_n1", {"fnc": calc_f_ploschad_kanala_m2_n1, "cell": "Excel O315"}),
("h_srednyaya_tolschina_plastin_m_n1", {"fnc": calc_h_srednyaya_tolschina_plastin_m_n1, "cell": "Excel O317"}),
("r_vnutrennij_radius_m_n2", {"fnc": calc_r_vnutrennij_radius_m_n2, "cell": "Excel O326"}),
("pk_izbytochnoe_davlenie_pod_kryshkoj_pa_2", {"fnc": calc_pk_izbytochnoe_davlenie_pod_kryshkoj_pa_2, "cell": "Excel O284"}),
("wk_skorost_na_vyhlope_v_atmosferu_m_s_2", {"fnc": calc_wk_skorost_na_vyhlope_v_atmosferu_m_s_2, "cell": "Excel O292"}),
("skorost_para_iz_truby_m_s", {"fnc": calc_skorost_para_iz_truby_m_s, "cell": "Excel O8"}),
("gidravlicheskij_diametr_m", {"fnc": calc_gidravlicheskij_diametr_m, "cell": "Excel O141"}),
("otnositelnaya_ploschad", {"fnc": calc_otnositelnaya_ploschad, "cell": "Excel O142"}),
("f_dh_0_5_n1", {"fnc": calc_f_dh_0_5_n1, "cell": "Excel O316"}),
("ds_n1", {"fnc": calc_ds_n1, "cell": "Excel O323"}),
("r_naruzhnyj_radius_m_n2", {"fnc": calc_r_naruzhnyj_radius_m_n2, "cell": "Excel O327"}),
("pk_izbytochnoe_davlenie_pod_kryshkoj_pa", {"fnc": calc_pk_izbytochnoe_davlenie_pod_kryshkoj_pa, "cell": "Excel O150"}),
("pa_izbytochnoe_davlenie_na_vyhode_iz_korpusa_za_stupenyu_zvukopogloscheniya_pa_2", {"fnc": calc_pa_izbytochnoe_davlenie_na_vyhode_iz_korpusa_za_stupenyu_zvukopogloscheniya_pa_2, "cell": "Excel O285"}),
("pk", {"fnc": calc_pk, "cell": "Excel O290"}),
("dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_bokovom_vyhlope_kn_2", {"fnc": calc_dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_bokovom_vyhlope_kn_2, "cell": "Excel O306"}),
("dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_osevom_vyhlope_kn_2", {"fnc": calc_dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_osevom_vyhlope_kn_2, "cell": "Excel O307"}),
("wk_skorost_na_vyhlope_v_atmosferu_m_s", {"fnc": calc_wk_skorost_na_vyhlope_v_atmosferu_m_s, "cell": "Excel O162"}),
("mk_chislo_maha_na_vyhlope_v_atmosferu_2", {"fnc": calc_mk_chislo_maha_na_vyhlope_v_atmosferu_2, "cell": "Excel O294"}),
("plotnost_rho_po_rashodu_i_geometrii", {"fnc": calc_plotnost_rho_po_rashodu_i_geometrii, "cell": "Excel O11"}),
("dh_gidravlicheskij_diametr_m_n2", {"fnc": calc_dh_gidravlicheskij_diametr_m_n2, "cell": "Excel O328"}),
("d_shirina_kanala_m_n2", {"fnc": calc_d_shirina_kanala_m_n2, "cell": "Excel O329"}),
("f_ploschad_kanala_m2_n2", {"fnc": calc_f_ploschad_kanala_m2_n2, "cell": "Excel O330"}),
("h_srednyaya_tolschina_plastin_m_n2", {"fnc": calc_h_srednyaya_tolschina_plastin_m_n2, "cell": "Excel O332"}),
("r_vnutrennij_radius_m_n3", {"fnc": calc_r_vnutrennij_radius_m_n3, "cell": "Excel O341"}),
("izbytochnoe_davlenie_pod_kryshkoj_ne_mozhet_prevyshat_15000_pa", {"fnc": calc_izbytochnoe_davlenie_pod_kryshkoj_ne_mozhet_prevyshat_15000_pa, "cell": "Excel O154"}),
("pa_izbytochnoe_davlenie_na_vyhode_iz_korpusa_za_stupenyu_zvukopogloscheniya_pa", {"fnc": calc_pa_izbytochnoe_davlenie_na_vyhode_iz_korpusa_za_stupenyu_zvukopogloscheniya_pa, "cell": "Excel O151"}),
("pa_absolyutnoe_davlenie_za_stupenyu_zvukopogloscheniya_pa_2", {"fnc": calc_pa_absolyutnoe_davlenie_za_stupenyu_zvukopogloscheniya_pa_2, "cell": "Excel O286"}),
("wa_skorost_na_vyhode_iz_korpusa_m_s_2", {"fnc": calc_wa_skorost_na_vyhode_iz_korpusa_m_s_2, "cell": "Excel O291"}),
("dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_bokovom_vyhlope_kn", {"fnc": calc_dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_bokovom_vyhlope_kn, "cell": "Excel O168"}),
("dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_osevom_vyhlope_kn", {"fnc": calc_dinamicheskaya_nagruzka_na_zaschitnuyu_kryshku_pri_osevom_vyhlope_kn, "cell": "Excel O169"}),
("mk_chislo_maha_na_vyhlope_v_atmosferu", {"fnc": calc_mk_chislo_maha_na_vyhlope_v_atmosferu, "cell": "Excel O164"}),
("k_mk", {"fnc": calc_k_mk, "cell": "Excel O296"}),
("f_dh_0_5_n2", {"fnc": calc_f_dh_0_5_n2, "cell": "Excel O331"}),
("ds_n2", {"fnc": calc_ds_n2, "cell": "Excel O338"}),
("r_naruzhnyj_radius_m_n3", {"fnc": calc_r_naruzhnyj_radius_m_n3, "cell": "Excel O342"}),
("izbytochnoe_davlenie_na_vyhode_iz_korpusa_za_stupenyu_zvukopogloscheniya_ne_mozhet_prevyshat_15000_pa", {"fnc": calc_izbytochnoe_davlenie_na_vyhode_iz_korpusa_za_stupenyu_zvukopogloscheniya_ne_mozhet_prevyshat_15000_pa, "cell": "Excel O155"}),
("pa_absolyutnoe_davlenie_za_stupenyu_zvukopogloscheniya_pa", {"fnc": calc_pa_absolyutnoe_davlenie_za_stupenyu_zvukopogloscheniya_pa, "cell": "Excel O152"}),
("pa_pa", {"fnc": calc_pa_pa, "cell": "Excel O265"}),
("wa_skorost_na_vyhode_iz_korpusa_m_s", {"fnc": calc_wa_skorost_na_vyhode_iz_korpusa_m_s, "cell": "Excel O161"}),
("ma_chislo_maha_na_vyhode_iz_korpusa_2", {"fnc": calc_ma_chislo_maha_na_vyhode_iz_korpusa_2, "cell": "Excel O293"}),
("wk_moschnost_shuma_na_vyhode_iz_pod_kryshki_vt", {"fnc": calc_wk_moschnost_shuma_na_vyhode_iz_pod_kryshki_vt, "cell": "Excel O298"}),
("dh_gidravlicheskij_diametr_m_n3", {"fnc": calc_dh_gidravlicheskij_diametr_m_n3, "cell": "Excel O343"}),
("d_shirina_kanala_m_n3", {"fnc": calc_d_shirina_kanala_m_n3, "cell": "Excel O344"}),
("f_ploschad_kanala_m2_n3", {"fnc": calc_f_ploschad_kanala_m2_n3, "cell": "Excel O345"}),
("r_vnutrennij_radius_m_n4", {"fnc": calc_r_vnutrennij_radius_m_n4, "cell": "Excel O356"}),
("v_skorost_mezhdu_plastinami_m_s", {"fnc": calc_v_skorost_mezhdu_plastinami_m_s, "cell": "Excel O10"}),
("ma_chislo_maha_na_vyhode_iz_korpusa", {"fnc": calc_ma_chislo_maha_na_vyhode_iz_korpusa, "cell": "Excel O163"}),
("k_ma", {"fnc": calc_k_ma, "cell": "Excel O295"}),
("lwk_uzm_generiruemyj_istecheniem_iz_pod_kryshki_db", {"fnc": calc_lwk_uzm_generiruemyj_istecheniem_iz_pod_kryshki_db, "cell": "Excel O300"}),
("h_srednyaya_tolschina_plastin_m_n3", {"fnc": calc_h_srednyaya_tolschina_plastin_m_n3, "cell": "Excel O347"}),
("f_dh_0_5_n3", {"fnc": calc_f_dh_0_5_n3, "cell": "Excel O346"}),
("r_naruzhnyj_radius_m_n4", {"fnc": calc_r_naruzhnyj_radius_m_n4, "cell": "Excel O357"}),
("k", {"fnc": calc_k, "cell": "Excel O13"}),
("wa_moschnost_shuma_na_vyhode_iz_korpusa_vt", {"fnc": calc_wa_moschnost_shuma_na_vyhode_iz_korpusa_vt, "cell": "Excel O297"}),
("ds_n3", {"fnc": calc_ds_n3, "cell": "Excel O353"}),
("dh_gidravlicheskij_diametr_m_n4", {"fnc": calc_dh_gidravlicheskij_diametr_m_n4, "cell": "Excel O358"}),
("d_shirina_kanala_m_n4", {"fnc": calc_d_shirina_kanala_m_n4, "cell": "Excel O359"}),
("f_ploschad_kanala_m2_n4", {"fnc": calc_f_ploschad_kanala_m2_n4, "cell": "Excel O360"}),
("r_vnutrennij_radius_m_n5", {"fnc": calc_r_vnutrennij_radius_m_n5, "cell": "Excel O371"}),
("lwa_uzm_generiruemyj_istecheniem_iz_korpusa_db", {"fnc": calc_lwa_uzm_generiruemyj_istecheniem_iz_korpusa_db, "cell": "Excel O299"}),
("h_srednyaya_tolschina_plastin_m_n4", {"fnc": calc_h_srednyaya_tolschina_plastin_m_n4, "cell": "Excel O362"}),
("f_dh_0_5_n4", {"fnc": calc_f_dh_0_5_n4, "cell": "Excel O361"}),
("r_naruzhnyj_radius_m_n5", {"fnc": calc_r_naruzhnyj_radius_m_n5, "cell": "Excel O372"}),
("ds_n4", {"fnc": calc_ds_n4, "cell": "Excel O368"}),
("dh_gidravlicheskij_diametr_m_n5", {"fnc": calc_dh_gidravlicheskij_diametr_m_n5, "cell": "Excel O373"}),
("d_shirina_kanala_m_n5", {"fnc": calc_d_shirina_kanala_m_n5, "cell": "Excel O374"}),
("f_ploschad_kanala_m2_n5", {"fnc": calc_f_ploschad_kanala_m2_n5, "cell": "Excel O375"}),
("r_vnutrennij_radius_m_n6", {"fnc": calc_r_vnutrennij_radius_m_n6, "cell": "Excel O386"}),
("h_srednyaya_tolschina_plastin_m_n5", {"fnc": calc_h_srednyaya_tolschina_plastin_m_n5, "cell": "Excel O377"}),
("f_dh_0_5_n5", {"fnc": calc_f_dh_0_5_n5, "cell": "Excel O376"}),
("r_naruzhnyj_radius_m_n6", {"fnc": calc_r_naruzhnyj_radius_m_n6, "cell": "Excel O387"}),
("ds_n5", {"fnc": calc_ds_n5, "cell": "Excel O383"}),
("dh_gidravlicheskij_diametr_m_n6", {"fnc": calc_dh_gidravlicheskij_diametr_m_n6, "cell": "Excel O388"}),
("d_shirina_kanala_m_n6", {"fnc": calc_d_shirina_kanala_m_n6, "cell": "Excel O389"}),
("f_ploschad_kanala_m2_n6", {"fnc": calc_f_ploschad_kanala_m2_n6, "cell": "Excel O390"}),
("h_srednyaya_tolschina_plastin_m_n6", {"fnc": calc_h_srednyaya_tolschina_plastin_m_n6, "cell": "Excel O39"}),
("ss_summarnaya_ploschad_vseh_kanalov_m2", {"fnc": calc_ss_summarnaya_ploschad_vseh_kanalov_m2, "cell": "Excel O260"}),
("f_dh_0_5_n6", {"fnc": calc_f_dh_0_5_n6, "cell": "Excel O391"}),
("ds_n6", {"fnc": calc_ds_n6, "cell": "Excel O39"}),
("f_otnositelnaya_ploschad", {"fnc": calc_f_otnositelnaya_ploschad, "cell": "Excel O262"}),
("summ_diam", {"fnc": calc_summ_diam, "cell": "Excel O261"}),
("ptr_pa", {"fnc": calc_ptr_pa, "cell": "Excel O266"}),
("pd_skorostnoj_napor_na_vyhode_pa_n1", {"fnc": calc_pd_skorostnoj_napor_na_vyhode_pa_n1, "cell": "Excel O318"}),
("g_rashod_v_kanale_kg_s_n1", {"fnc": calc_g_rashod_v_kanale_kg_s_n1, "cell": "Excel O319"}),
("pd_skorostnoj_napor_na_vyhode_pa_n2", {"fnc": calc_pd_skorostnoj_napor_na_vyhode_pa_n2, "cell": "Excel O333"}),
("g_rashod_v_kanale_kg_s_n2", {"fnc": calc_g_rashod_v_kanale_kg_s_n2, "cell": "Excel O334"}),
("pd_skorostnoj_napor_na_vyhode_pa_n3", {"fnc": calc_pd_skorostnoj_napor_na_vyhode_pa_n3, "cell": "Excel O348"}),
("g_rashod_v_kanale_kg_s_n3", {"fnc": calc_g_rashod_v_kanale_kg_s_n3, "cell": "Excel O349"}),
("pd_skorostnoj_napor_na_vyhode_pa_n4", {"fnc": calc_pd_skorostnoj_napor_na_vyhode_pa_n4, "cell": "Excel O363"}),
("g_rashod_v_kanale_kg_s_n4", {"fnc": calc_g_rashod_v_kanale_kg_s_n4, "cell": "Excel O364"}),
("pd_skorostnoj_napor_na_vyhode_pa_n5", {"fnc": calc_pd_skorostnoj_napor_na_vyhode_pa_n5, "cell": "Excel O378"}),
("g_rashod_v_kanale_kg_s_n5", {"fnc": calc_g_rashod_v_kanale_kg_s_n5, "cell": "Excel O379"}),
("pd_skorostnoj_napor_na_vyhode_pa_n6", {"fnc": calc_pd_skorostnoj_napor_na_vyhode_pa_n6, "cell": "Excel O39"}),
("g_rashod_v_kanale_kg_s_n6", {"fnc": calc_g_rashod_v_kanale_kg_s_n6, "cell": "Excel O39"}),
("v_aero", {"fnc": calc_v_aero, "cell": "Excel O269"}),
("plotnost_rho_po_idealnomu_gazu", {"fnc": calc_plotnost_rho_po_idealnomu_gazu, "cell": "Excel O270"}),
("w_skorost_v_kanale_m_s_n1", {"fnc": calc_w_skorost_v_kanale_m_s_n1, "cell": "Excel O320"}),
("w_skorost_v_kanale_m_s_n2", {"fnc": calc_w_skorost_v_kanale_m_s_n2, "cell": "Excel O335"}),
("w_skorost_v_kanale_m_s_n3", {"fnc": calc_w_skorost_v_kanale_m_s_n3, "cell": "Excel O350"}),
("w_skorost_v_kanale_m_s_n4", {"fnc": calc_w_skorost_v_kanale_m_s_n4, "cell": "Excel O365"}),
("w_skorost_v_kanale_m_s_n5", {"fnc": calc_w_skorost_v_kanale_m_s_n5, "cell": "Excel O380"}),
("pd_srednij_skorostnoj_napor_na_vyhode_iz_schelevyh_kanalov", {"fnc": calc_pd_srednij_skorostnoj_napor_na_vyhode_iz_schelevyh_kanalov, "cell": "Excel O14"}),
("w_skorost_v_kanale_m_s_n6", {"fnc": calc_w_skorost_v_kanale_m_s_n6, "cell": "Excel O39"}),
("pi3_davlenie_pered_stupenyu_zvukopogloscheniya_pa_2", {"fnc": calc_pi3_davlenie_pered_stupenyu_zvukopogloscheniya_pa_2, "cell": "Excel O267"}),
("m_chislo_maha_v_kanale_n1", {"fnc": calc_m_chislo_maha_v_kanale_n1, "cell": "Excel O321"}),
("m_chislo_maha_v_kanale_n2", {"fnc": calc_m_chislo_maha_v_kanale_n2, "cell": "Excel O336"}),
("m_chislo_maha_v_kanale_n3", {"fnc": calc_m_chislo_maha_v_kanale_n3, "cell": "Excel O351"}),
("m_chislo_maha_v_kanale_n4", {"fnc": calc_m_chislo_maha_v_kanale_n4, "cell": "Excel O366"}),
("m_chislo_maha_v_kanale_n5", {"fnc": calc_m_chislo_maha_v_kanale_n5, "cell": "Excel O381"}),
("maksimalnaya_skorost_mezhdu_kasset_m_s", {"fnc": calc_maksimalnaya_skorost_mezhdu_kasset_m_s, "cell": "Excel O26"}),
("m_chislo_maha_v_kanale_n6", {"fnc": calc_m_chislo_maha_v_kanale_n6, "cell": "Excel O39"}),
("pi3_davlenie_pered_stupenyu_zvukopogloscheniya_pa", {"fnc": calc_pi3_davlenie_pered_stupenyu_zvukopogloscheniya_pa, "cell": "Excel O153"}),
("dinamicheskaya_nagruzka_na_stupen_zvukopogloscheniya_kn_2", {"fnc": calc_dinamicheskaya_nagruzka_na_stupen_zvukopogloscheniya_kn_2, "cell": "Excel O305"}),
("k_m_n1", {"fnc": calc_k_m_n1, "cell": "Excel O322"}),
("k_m_n2", {"fnc": calc_k_m_n2, "cell": "Excel O337"}),
("k_m_n3", {"fnc": calc_k_m_n3, "cell": "Excel O352"}),
("k_m_n4", {"fnc": calc_k_m_n4, "cell": "Excel O367"}),
("k_m_n5", {"fnc": calc_k_m_n5, "cell": "Excel O382"}),
("k_m_n6", {"fnc": calc_k_m_n6, "cell": "Excel O39"}),
("davlenie_na_vyhode_iz_shg_pe_mpa", {"fnc": calc_davlenie_na_vyhode_iz_shg_pe_mpa, "cell": "Excel O27"}),
("dinamicheskaya_nagruzka_na_stupen_zvukopogloscheniya_kn", {"fnc": calc_dinamicheskaya_nagruzka_na_stupen_zvukopogloscheniya_kn, "cell": "Excel O171"}),
("ws_moschnost_shuma_na_vyhode_kanala_vt_n1", {"fnc": calc_ws_moschnost_shuma_na_vyhode_kanala_vt_n1, "cell": "Excel O324"}),
("ws_moschnost_shuma_na_vyhode_kanala_vt_n2", {"fnc": calc_ws_moschnost_shuma_na_vyhode_kanala_vt_n2, "cell": "Excel O339"}),
("ws_moschnost_shuma_na_vyhode_kanala_vt_n3", {"fnc": calc_ws_moschnost_shuma_na_vyhode_kanala_vt_n3, "cell": "Excel O354"}),
("ws_moschnost_shuma_na_vyhode_kanala_vt_n4", {"fnc": calc_ws_moschnost_shuma_na_vyhode_kanala_vt_n4, "cell": "Excel O369"}),
("ws_moschnost_shuma_na_vyhode_kanala_vt_n5", {"fnc": calc_ws_moschnost_shuma_na_vyhode_kanala_vt_n5, "cell": "Excel O384"}),
("ws_moschnost_shuma_na_vyhode_kanala_vt_n6", {"fnc": calc_ws_moschnost_shuma_na_vyhode_kanala_vt_n6, "cell": "Excel O39"}),
("znachenie_p_drosselnogo_bloka", {"fnc": calc_znachenie_p_drosselnogo_bloka, "cell": "Excel O30"}),
("davlenie_za_reshetkami_mpa_n10", {"fnc": calc_davlenie_za_reshetkami_mpa_n10, "cell": "Excel O244"}),
("lws_n1", {"fnc": calc_lws_n1, "cell": "Excel O325"}),
("lws_n2", {"fnc": calc_lws_n2, "cell": "Excel O340"}),
("lws_n3", {"fnc": calc_lws_n3, "cell": "Excel O355"}),
("lws_n4", {"fnc": calc_lws_n4, "cell": "Excel O370"}),
("lws_n5", {"fnc": calc_lws_n5, "cell": "Excel O385"}),
("lws_n6", {"fnc": calc_lws_n6, "cell": "Excel O40"}),
("maksimalnyj_gradient_skorosti_wmax", {"fnc": calc_maksimalnyj_gradient_skorosti_wmax, "cell": "Excel O39"}),
("rekomenduemoe_nachalnoe_znachenie_w", {"fnc": calc_rekomenduemoe_nachalnoe_znachenie_w, "cell": "Excel O40"}),
("gradient_skorosti_w", {"fnc": calc_gradient_skorosti_w, "cell": "Excel O38"}),
("otnositelnyj_perepad_davleniya_na_poslednej_reshetke", {"fnc": calc_otnositelnyj_perepad_davleniya_na_poslednej_reshetke, "cell": "Excel O42"}),
("perepad_davlenij_n10", {"fnc": calc_perepad_davlenij_n10, "cell": "Excel O82"}),
("perepad_davlenij_n9", {"fnc": calc_perepad_davlenij_n9, "cell": "Excel O78"}),
("gazodinamicheskaya_funkciya_rashoda_q_n10", {"fnc": calc_gazodinamicheskaya_funkciya_rashoda_q_n10, "cell": "Excel O83"}),
("perepad_davlenij_n8", {"fnc": calc_perepad_davlenij_n8, "cell": "Excel O74"}),
("gazodinamicheskaya_funkciya_rashoda_q_n9", {"fnc": calc_gazodinamicheskaya_funkciya_rashoda_q_n9, "cell": "Excel O79"}),
("oblast_n10", {"fnc": calc_oblast_n10, "cell": "Excel O84"}),
("perepad_davlenij_n7", {"fnc": calc_perepad_davlenij_n7, "cell": "Excel O70"}),
("gazodinamicheskaya_funkciya_rashoda_q_n8", {"fnc": calc_gazodinamicheskaya_funkciya_rashoda_q_n8, "cell": "Excel O75"}),
("oblast_n9", {"fnc": calc_oblast_n9, "cell": "Excel O80"}),
("perepad_davlenij_n6", {"fnc": calc_perepad_davlenij_n6, "cell": "Excel O66"}),
("gazodinamicheskaya_funkciya_rashoda_q_n7", {"fnc": calc_gazodinamicheskaya_funkciya_rashoda_q_n7, "cell": "Excel O71"}),
("oblast_n8", {"fnc": calc_oblast_n8, "cell": "Excel O76"}),
("perepad_davlenij_n5", {"fnc": calc_perepad_davlenij_n5, "cell": "Excel O62"}),
("gazodinamicheskaya_funkciya_rashoda_q_n6", {"fnc": calc_gazodinamicheskaya_funkciya_rashoda_q_n6, "cell": "Excel O67"}),
("oblast_n7", {"fnc": calc_oblast_n7, "cell": "Excel O72"}),
("perepad_davlenij_n4", {"fnc": calc_perepad_davlenij_n4, "cell": "Excel O58"}),
("gazodinamicheskaya_funkciya_rashoda_q_n5", {"fnc": calc_gazodinamicheskaya_funkciya_rashoda_q_n5, "cell": "Excel O63"}),
("oblast_n6", {"fnc": calc_oblast_n6, "cell": "Excel O68"}),
("perepad_davlenij_n3", {"fnc": calc_perepad_davlenij_n3, "cell": "Excel O54"}),
("gazodinamicheskaya_funkciya_rashoda_q_n4", {"fnc": calc_gazodinamicheskaya_funkciya_rashoda_q_n4, "cell": "Excel O59"}),
("oblast_n4", {"fnc": calc_oblast_n4, "cell": "Excel O60"}),
("oblast_n5", {"fnc": calc_oblast_n5, "cell": "Excel O64"}),
("perepad_davlenij_n2", {"fnc": calc_perepad_davlenij_n2, "cell": "Excel O50"}),
("gazodinamicheskaya_funkciya_rashoda_q_n3", {"fnc": calc_gazodinamicheskaya_funkciya_rashoda_q_n3, "cell": "Excel O55"}),
("oblast_n3", {"fnc": calc_oblast_n3, "cell": "Excel O56"}),
("perepad_davlenij_n1", {"fnc": calc_perepad_davlenij_n1, "cell": "Excel O46"}),
("gazodinamicheskaya_funkciya_rashoda_q_n2", {"fnc": calc_gazodinamicheskaya_funkciya_rashoda_q_n2, "cell": "Excel O51"}),
("oblast_n2", {"fnc": calc_oblast_n2, "cell": "Excel O52"}),
("gazodinamicheskaya_funkciya_rashoda_q_n1", {"fnc": calc_gazodinamicheskaya_funkciya_rashoda_q_n1, "cell": "Excel O47"}),
("oblast_n1", {"fnc": calc_oblast_n1, "cell": "Excel O48"}),
("prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n1", {"fnc": calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n1, "cell": "Excel O92"}),
("diametry_otverstij_mm_n1", {"fnc": calc_diametry_otverstij_mm_n1, "cell": "Excel O91"}),
("minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n1", {"fnc": calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n1, "cell": "Excel O93"}),
("prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n2", {"fnc": calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n2, "cell": "Excel O96"}),
("prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n3", {"fnc": calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n3, "cell": "Excel O100"}),
("prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n4", {"fnc": calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n4, "cell": "Excel O104"}),
("prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n5", {"fnc": calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n5, "cell": "Excel O108"}),
("prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n6", {"fnc": calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n6, "cell": "Excel O112"}),
("prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n7", {"fnc": calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n7, "cell": "Excel O116"}),
("prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n8", {"fnc": calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n8, "cell": "Excel O120"}),
("prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n9", {"fnc": calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n9, "cell": "Excel O124"}),
("prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n10", {"fnc": calc_prohodnye_ploschadi_drosselnyh_reshetok_fi_mm2_n10, "cell": "Excel O128"}),
("diametry_otverstij_mm_n2", {"fnc": calc_diametry_otverstij_mm_n2, "cell": "Excel O95"}),
("minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n2", {"fnc": calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n2, "cell": "Excel O97"}),
("diametry_otverstij_mm_n3", {"fnc": calc_diametry_otverstij_mm_n3, "cell": "Excel O99"}),
("minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n3", {"fnc": calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n3, "cell": "Excel O101"}),
("diametry_otverstij_mm_n4", {"fnc": calc_diametry_otverstij_mm_n4, "cell": "Excel O103"}),
("minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n4", {"fnc": calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n4, "cell": "Excel O105"}),
("diametry_otverstij_mm_n5", {"fnc": calc_diametry_otverstij_mm_n5, "cell": "Excel O107"}),
("minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n5", {"fnc": calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n5, "cell": "Excel O109"}),
("diametry_otverstij_mm_n6", {"fnc": calc_diametry_otverstij_mm_n6, "cell": "Excel O111"}),
("minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n6", {"fnc": calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n6, "cell": "Excel O113"}),
("diametry_otverstij_mm_n7", {"fnc": calc_diametry_otverstij_mm_n7, "cell": "Excel O115"}),
("minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n7", {"fnc": calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n7, "cell": "Excel O117"}),
("diametry_otverstij_mm_n8", {"fnc": calc_diametry_otverstij_mm_n8, "cell": "Excel O119"}),
("minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n8", {"fnc": calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n8, "cell": "Excel O121"}),
("diametry_otverstij_mm_n9", {"fnc": calc_diametry_otverstij_mm_n9, "cell": "Excel O123"}),
("minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n9", {"fnc": calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n9, "cell": "Excel O125"}),
("diametry_otverstij_mm_n10", {"fnc": calc_diametry_otverstij_mm_n10, "cell": "Excel O127"}),
("minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n10", {"fnc": calc_minimalnye_ploschadi_drosselnyh_reshetok_trebuemye_dlya_razmescheniya_otverstij_ftr_mm2_n10, "cell": "Excel O129"}),
("y_n10", {"fnc": calc_y_n10, "cell": "Excel O245"}),
("n10", {"fnc": calc_n10, "cell": "Excel O247"}),
("n10_2", {"fnc": calc_n10_2, "cell": "Excel O248"}),
("n10_3", {"fnc": calc_n10_3, "cell": "Excel O249"}),
("perepad_davlenij_n10_2", {"fnc": calc_perepad_davlenij_n10_2, "cell": "Excel O246"}),
("davlenie_za_reshetkami_mpa_n9", {"fnc": calc_davlenie_za_reshetkami_mpa_n9, "cell": "Excel O237"}),
("y_n9", {"fnc": calc_y_n9, "cell": "Excel O238"}),
("n9", {"fnc": calc_n9, "cell": "Excel O240"}),
("n9_2", {"fnc": calc_n9_2, "cell": "Excel O241"}),
("n9_3", {"fnc": calc_n9_3, "cell": "Excel O242"}),
("perepad_davlenij_n9_2", {"fnc": calc_perepad_davlenij_n9_2, "cell": "Excel O239"}),
("davlenie_za_reshetkami_mpa_n8", {"fnc": calc_davlenie_za_reshetkami_mpa_n8, "cell": "Excel O230"}),
("y_n8", {"fnc": calc_y_n8, "cell": "Excel O231"}),
("n8", {"fnc": calc_n8, "cell": "Excel O233"}),
("n8_2", {"fnc": calc_n8_2, "cell": "Excel O234"}),
("n8_3", {"fnc": calc_n8_3, "cell": "Excel O235"}),
("perepad_davlenij_n8_2", {"fnc": calc_perepad_davlenij_n8_2, "cell": "Excel O232"}),
("davlenie_za_reshetkami_mpa_n7", {"fnc": calc_davlenie_za_reshetkami_mpa_n7, "cell": "Excel O223"}),
("y_n7", {"fnc": calc_y_n7, "cell": "Excel O224"}),
("n7", {"fnc": calc_n7, "cell": "Excel O226"}),
("n7_2", {"fnc": calc_n7_2, "cell": "Excel O227"}),
("n7_3", {"fnc": calc_n7_3, "cell": "Excel O228"}),
("perepad_davlenij_n7_2", {"fnc": calc_perepad_davlenij_n7_2, "cell": "Excel O225"}),
("davlenie_za_reshetkami_mpa_n6", {"fnc": calc_davlenie_za_reshetkami_mpa_n6, "cell": "Excel O216"}),
("y_n6", {"fnc": calc_y_n6, "cell": "Excel O217"}),
("n6", {"fnc": calc_n6, "cell": "Excel O219"}),
("n6_2", {"fnc": calc_n6_2, "cell": "Excel O220"}),
("n6_3", {"fnc": calc_n6_3, "cell": "Excel O221"}),
("perepad_davlenij_n6_2", {"fnc": calc_perepad_davlenij_n6_2, "cell": "Excel O218"}),
("davlenie_za_reshetkami_mpa_n5", {"fnc": calc_davlenie_za_reshetkami_mpa_n5, "cell": "Excel O209"}),
("y_n5", {"fnc": calc_y_n5, "cell": "Excel O210"}),
("n5", {"fnc": calc_n5, "cell": "Excel O212"}),
("n5_2", {"fnc": calc_n5_2, "cell": "Excel O213"}),
("n5_3", {"fnc": calc_n5_3, "cell": "Excel O214"}),
("perepad_davlenij_n5_2", {"fnc": calc_perepad_davlenij_n5_2, "cell": "Excel O211"}),
("davlenie_za_reshetkami_mpa_n4", {"fnc": calc_davlenie_za_reshetkami_mpa_n4, "cell": "Excel O202"}),
("y_n4", {"fnc": calc_y_n4, "cell": "Excel O203"}),
("n4", {"fnc": calc_n4, "cell": "Excel O205"}),
("n4_2", {"fnc": calc_n4_2, "cell": "Excel O206"}),
("n4_3", {"fnc": calc_n4_3, "cell": "Excel O207"}),
("perepad_davlenij_n4_2", {"fnc": calc_perepad_davlenij_n4_2, "cell": "Excel O204"}),
("davlenie_za_reshetkami_mpa_n3", {"fnc": calc_davlenie_za_reshetkami_mpa_n3, "cell": "Excel O195"}),
("y_n3", {"fnc": calc_y_n3, "cell": "Excel O196"}),
("n3", {"fnc": calc_n3, "cell": "Excel O198"}),
("n3_2", {"fnc": calc_n3_2, "cell": "Excel O199"}),
("n3_3", {"fnc": calc_n3_3, "cell": "Excel O200"}),
("perepad_davlenij_n3_2", {"fnc": calc_perepad_davlenij_n3_2, "cell": "Excel O197"}),
("davlenie_za_reshetkami_mpa_n2", {"fnc": calc_davlenie_za_reshetkami_mpa_n2, "cell": "Excel O188"}),
("y_n2", {"fnc": calc_y_n2, "cell": "Excel O189"}),
("n2", {"fnc": calc_n2, "cell": "Excel O191"}),
("n2_2", {"fnc": calc_n2_2, "cell": "Excel O192"}),
("n2_3", {"fnc": calc_n2_3, "cell": "Excel O193"}),
("perepad_davlenij_n2_2", {"fnc": calc_perepad_davlenij_n2_2, "cell": "Excel O190"}),
("davlenie_za_reshetkami_mpa_n1", {"fnc": calc_davlenie_za_reshetkami_mpa_n1, "cell": "Excel O181"}),
("y_n1", {"fnc": calc_y_n1, "cell": "Excel O182"}),
("n1", {"fnc": calc_n1, "cell": "Excel O184"}),
("n1_2", {"fnc": calc_n1_2, "cell": "Excel O185"}),
("n1_3", {"fnc": calc_n1_3, "cell": "Excel O186"}),
("perepad_davlenij_n1_2", {"fnc": calc_perepad_davlenij_n1_2, "cell": "Excel O183"}),
("davlenie_za_reshetkami_mpa_n0", {"fnc": calc_davlenie_za_reshetkami_mpa_n0, "cell": "Excel O174"}),
("y", {"fnc": calc_y, "cell": "Excel O15"}),
("λ", {"fnc": calc_λ, "cell": "Excel O16"}),
("dinamicheskaya_nagruzka_na_drosselnyj_blok_kn_2", {"fnc": calc_dinamicheskaya_nagruzka_na_drosselnyj_blok_kn_2, "cell": "Excel O304"}),
("dinamicheskaya_nagruzka_na_drosselnyj_blok_kn", {"fnc": calc_dinamicheskaya_nagruzka_na_drosselnyj_blok_kn, "cell": "Excel O170"}),
("davlenie_na_dnische_drosselnogo_bloka_mpa", {"fnc": calc_davlenie_na_dnische_drosselnogo_bloka_mpa, "cell": "Excel O308"}),
                              ('udelnyj_obem_m3_kg_out', {"fnc":calc_udelnyj_obem_m3_kg_out, "cell":"input tbl"}),
                               ('massovyj_rashod_kg_s_out', {"fnc":calc_massovyj_rashod_kg_s_out, "cell":"input tbl"}),
                                ('diametr_shg_m_out', {"fnc":calc_diametr_shg_m_out, "cell":"input tbl"}),
                              ('udelnyj_obem_m3_kg_out2', {"fnc":calc_udelnyj_obem_m3_kg_out, "cell":"input tbl"}),
                               ('massovyj_rashod_kg_s_out2', {"fnc":calc_massovyj_rashod_kg_s_out, "cell":"input tbl"}),
                                ('diametr_shg_m_out2', {"fnc":calc_diametr_shg_m_out, "cell":"input tbl"}),
                                 ('koefficient_treniya_out', {"fnc":calc_koefficient_treniya_out, "cell":"input tbl"}),
                                  ('atmosfernoe_davlenie_pa_out', {"fnc":calc_atmosfernoe_davlenie_pa_out, "cell":"input tbl"}),

                              ])

