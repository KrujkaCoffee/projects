using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text.RegularExpressions;
using System.Threading;
using System.Reflection;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Web.Script.Serialization;
using TFlex.DOCs.Model.Macros;
using TFlex.DOCs.Model.Macros.ObjectModel;
using TFlex.DOCs.Model.Notification.ServerTasks;
using TFlex.DOCs.Model.Notification.ServerTasks.Handlers;
using TFlex.DOCs.Model.Notification.ServerTasks.Triggers;
using TFlex.DOCs.Model.References;

public class Macro : MacroProvider
{
    private const string MacroName = "Б24. Передача на сервер";
    private const string ReceiverMethod = "ПринятьПроверкуТКПНаСервере";
    private const int ScheduleDelaySeconds = 60;

    public Macro(MacroContext context) : base(context) { }

    public override void Run()
    {
    ОтправитьТестБ24НаСервере();
//        throw new InvalidOperationException("SELECT_EXPLICIT_HANDOFF_METHOD");
    }

    // Вызывать АДМИНИСТРАТОРОМ из временной кнопки на одном процессе «Процессы ТКП 2».
    // Клиентский метод не читает файлы конфигурации/журналы.
    public void ПоставитьПроверкуТКПНаСервер()
    {
        QueuePilot(true);
    }

    private void QueuePilot(bool testB24)
    {
        RequireAdminClient();
        Объект process = ТекущийОбъект;
        if (process == null || process.Тип == "Папка")
            throw new InvalidOperationException("SELECT_ONE_TKP_PROCESS");
        Объект known = НайтиОбъект("Процессы ТКП 2", "[ID] = " + process.Id.ToString(CultureInfo.InvariantCulture));
        if (known == null || (ReferenceObject)known != (ReferenceObject)process)
            throw new InvalidOperationException("SELECT_OBJECT_FROM_TKP2_REFERENCE");
        if (МестоОтправкиИзНастроектПроцессаТкп() == 0)
            throw new InvalidOperationException("TKP_NOTIFICATIONS_DISABLED");

        Объект stage = process.СвязанныйОбъект["Этап"];
        string status = process.Параметр["Статус"];
        if (stage == null && status != "Завершён" && status != "Отменён")
            throw new InvalidOperationException("SELECT_STARTED_OR_FINISHED_PROCESS");
        List<Объект> users = stage != null
            ? АдресатыЗадачиЭтапа(process, stage)
            : АдресатыОкончанияПроцесса(process);
        if (users.Count == 0) throw new InvalidOperationException("NO_RECIPIENTS_AFTER_TKP_FILTER");

        var dialog = СоздатьДиалогВвода(testB24
            ? "Б24: тест серверного канала на TestUserId"
            : "Б24: передать снимок на сервер без отправки");
        dialog.ДобавитьСтроковое("Комментарий проверки", "Проверка передачи: русский текст, «кавычки», DOCs → сервер.");
        if (!dialog.Показать()) return;
        string comment = dialog["Комментарий проверки"];
        var packet = BuildPacket(process, stage, users, status, comment);
        if (testB24)
        {
            if (!Вопрос("Создать серверную задачу ТЕСТА Б24?\n"
                + "Адресат — только TestUserId из закрытого серверного конфига.\n"
                + "DryRun=true: проверка без сообщения; DryRun=false: одна попытка отправки.\n"
                + "Содержимое выбранного процесса будет включено в тестовое сообщение.\n"
                + "Исходные получатели процесса не используются для доставки.")) return;
            packet.Schema = 2;
            packet.Mode = "SERVER_TEST_ONLY";
        }
        string data = HandoffWire.Encode(packet);
        var receiver = Context.Connection.References.Macros.Find(MacroName);
        if (receiver == null) throw new InvalidOperationException("HANDOFF_MACRO_NOT_FOUND_BY_NAME");

        ServerTask task = Context.Connection.ServerTaskManager.CreateTask();
        string name = (testB24 ? "Б24 SENDTEST " : "Б24 TEST ") + packet.RequestId;
        task.Name = name;
        task.Comment = testB24
            ? "ADMIN SERVER_TEST_ONLY: только серверный TestUserId, DryRun берётся на сервере."
            : "Проверка передачи ТКП. PREVIEW_ONLY: почта и Б24 не отправляются.";
        task.Action = new MacroTaskAction(Context.Connection, receiver.Guid, testB24 ? "ОтправитьТестБ24НаСервере" : ReceiverMethod) { Data = data };
        DateTime start = DateTime.Now.AddSeconds(ScheduleDelaySeconds);
        task.Trigger = new TimeTrigger { StartTime = start };
        task.Enabled = true;
        bool saved;
        try { saved = task.Save(); }
        catch (Exception ex)
        {
            throw new InvalidOperationException("TASK_SAVE_RESULT_UNKNOWN; error_type=" + ex.GetType().FullName + "; check task name before retry: " + name);
        }
        if (!saved) throw new InvalidOperationException("TASK_SAVE_RETURNED_FALSE; check task name: " + name);
        Сообщение("Б24: задача сохранена", (testB24 ? "QUEUED_SERVER_TEST\n" : "QUEUED_FOR_PREVIEW\n")
            + "Имя задачи: " + name + "\n"
            + "ID задачи DOCs: " + task.Id + "\n"
            + "Начало по часам клиента: " + start.ToString("yyyy-MM-dd HH:mm:ss") + "\n"
            + "Получателей DOCs в снимке: " + packet.Recipients.Count + "\n"
            + "Это ещё не серверное выполнение и не доставка Б24.\n"
            + " / B24\\Server\\Reports / " + (testB24 ? "b24-test-" : "handoff-") + packet.RequestId + "-*.txt");
    }

    public void ПринятьПроверкуТКПНаСервере()
    {
        HandoffServer.RequireServer();
        TaskActionContext context = Context as TaskActionContext;
        if (context == null) throw new InvalidOperationException("TASK_ACTION_CONTEXT_REQUIRED");
        HandoffServer.RequireProtectedDirectory(HandoffServer.Root);
        string reports = Path.Combine(HandoffServer.Root, "Reports");
        HandoffServer.RequireProtectedDirectory(reports);

        HandoffPacket packet = HandoffWire.Decode(context.MacroTaskActionData);
        if (packet.Schema != 1 || packet.Mode != "PREVIEW_ONLY")
            throw new InvalidOperationException("PREVIEW_PACKET_REQUIRED");
        var text = new StringBuilder();
        text.AppendLine("TFLEX DOCs / Б24: принят снимок уведомления");
        text.AppendLine("Результат: RECEIVED_ON_SERVER");
        text.AppendLine("Режим: PREVIEW_ONLY; в этом режиме нет чтения конфига и вызовов Б24");
        text.AppendLine("UTC приёма: " + DateTime.UtcNow.ToString("O"));
        text.AppendLine("Компьютер: " + Environment.MachineName);
        using (var process = Process.GetCurrentProcess())
            text.AppendLine("Процесс: " + process.ProcessName);
        text.AppendLine("Контекст: " + Context.GetType().FullName);
        text.AppendLine("Сборка Model: " + typeof(MacroContext).Assembly.FullName);
        text.AppendLine("Текущий пользователь DOCs: " + ТекущийПользователь + "; ID=" + ТекущийПользователь.Id);
        text.AppendLine("Задача DOCs: " + (context.Task == null ? "<нет>" : context.Task.Id.ToString(CultureInfo.InvariantCulture)));
        text.AppendLine("RequestId: " + packet.RequestId);
        text.AppendLine("Снимок записан клиентом UTC: " + packet.CreatedUtc);
        text.AppendLine("Компьютер источника (из данных): " + packet.SourceMachine);
        text.AppendLine("Инициатор DOCs ID (из данных): " + packet.SourceDocsUserId);
        text.AppendLine("Целостность сериализации: SHA256_MATCH");
        text.AppendLine("Хэш проверяет передачу байтов, а не подлинность инициатора.");
        text.AppendLine("Процесс ТКП ID=" + packet.ProcessId + "; справочник ID=" + packet.ProcessReferenceId);
        text.AppendLine("Этап ID=" + packet.StageId + "; получателей DOCs=" + packet.Recipients.Count);
        text.AppendLine("Секрет/конфигурация не читались. Вызовов Б24: 0. Почтовых сообщений: 0.");
        text.AppendLine("Данные процесса и действий не изменялись.");
        text.AppendLine("--- Снимок (JSON; строки экранированы, данные из выбранного процесса) ---");
        text.AppendLine(HandoffWire.Serializer().Serialize(packet));
        string path = Path.Combine(reports, "handoff-" + packet.RequestId + "-"
            + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-fff") + "-" + Guid.NewGuid().ToString("N") + ".txt");
        try
        {
            using (var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
            using (var writer = new StreamWriter(stream, new UTF8Encoding(true)))
                writer.Write(text.ToString());
        }
        catch (Exception) { throw new InvalidOperationException("HANDOFF_REPORT_WRITE_FAILED"); }
    }

    public void ОтправитьТестБ24НаСервере()
    {
        HandoffServer.RequireServer();
        TaskActionContext context = Context as TaskActionContext;
        if (context == null) throw new InvalidOperationException("TASK_ACTION_CONTEXT_REQUIRED");
        HandoffPacket packet;
        try { packet = HandoffWire.Decode(context.MacroTaskActionData); }
        catch (Exception) { throw new InvalidOperationException("INVALID_SERVER_TEST_PACKET"); }
        if (packet.Schema != 2 || packet.Mode != "SERVER_TEST_ONLY")
            throw new InvalidOperationException("TEST_PACKET_REQUIRED_NO_PREVIEW_REPLAY");
        B24ServerTest.Run(packet, context.Task == null ? "<нет>" : context.Task.Id.ToString(CultureInfo.InvariantCulture));
    }

    private void RequireAdminClient()
    {
        if (!Context.IsAdministrator) throw new InvalidOperationException("ADMIN_HANDOFF_PILOT_ONLY");
        using (var process = Process.GetCurrentProcess())
            if (!String.Equals(process.ProcessName, "TFlex.DOCs.Client", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("START_HANDOFF_FROM_CLIENT_BUTTON");
        if (Context is TaskActionContext) throw new InvalidOperationException("DO_NOT_SCHEDULE_PRODUCER_METHOD");
    }

    private HandoffPacket BuildPacket(Объект process, Объект stage, List<Объект> users, string status, string comment)
    {
        string name = process.ToString().Replace("__Процесс ТКП", String.Empty);
        string suffix = stage != null ? "Этап " + stage : (status == "Отменён" ? "Процесс отменён" : "Процесс завершён");
        string server = ГлобальныйПараметр["Имя сервера"];
        int referenceId = Context.Connection.ReferenceCatalog.Find("Процессы ТКП 2").Id;
        var packet = new HandoffPacket {
            Schema = 1, Mode = "PREVIEW_ONLY", RequestId = Guid.NewGuid().ToString("N"),
            CreatedUtc = DateTime.UtcNow.ToString("O"), SourceMachine = Environment.MachineName,
            SourceDocsUserId = ТекущийПользователь.Id, ProcessReferenceId = referenceId,
            ProcessId = process.Id, StageId = stage == null ? 0 : stage.Id,
            Title = "DOCs. Процесс ТКП. " + name + ". " + suffix,
            Kind = stage != null ? "Задача" : "Уведомление",
            TaskText = stage != null ? "Выполните необходимые действия для этапа" : suffix,
            Comment = comment ?? "", ProcessNameWithDate = name + " от " + process.Параметр["Дата запуска"].ToString(),
            StageName = stage == null ? "" : stage.ToString(),
            ProcessUrl = "docs://" + server + "/OpenReferenceWindow/?refId=" + referenceId + "&objId=" + process.Id,
            CardUrl = "", Recipients = new List<HandoffRecipient>()
        };
        Объект card = process.СвязанныйОбъект["Карточка проекта"];
        if (card != null)
            packet.CardUrl = "docs://" + server + "/OpenPropertiesInNewWindow/?refId="
                + Context.Connection.ReferenceCatalog.Find("Карточки проектов").Id + "&objId=" + card.Id;
        var ids = new HashSet<int>();
        foreach (Объект user in users)
        {
            if (user == null || !ids.Add(user.Id)) continue;
            string email = user.Параметр["Электронная почта"];
            packet.Recipients.Add(new HandoffRecipient { DocsId = user.Id, Name = user.ToString(), Email = email ?? "" });
        }
        HandoffWire.Validate(packet);
        return packet;
    }

    private List<Объект> ФильтрПоТипуПользователя(List<Объект> ГруппыАдресатов)
    {
        List<string> ТипыПользователей = new List<string>()
        {
            "Администратор",
            "Сотрудник"
        };

        List<Объект> Адресаты = new List<Объект>();

        foreach (Объект об in ГруппыАдресатов)
        {
            //if (об.Параметр["Тип"] == "Администратор" || об.Параметр["Тип"] == "Сотрудник")
            if (ТипыПользователей.Contains(об.Тип))
                if (!Адресаты.Contains(об))
                    Адресаты.Add(об);

            foreach (Объект об_у2 in об.ВсеДочерниеОбъекты)
            {
                //if (об_у2.Параметр["Тип"] == "Администратор" || об_у2.Параметр["Тип"] == "Сотрудник")
                if (ТипыПользователей.Contains(об_у2.Тип))
                    if (!Адресаты.Contains(об_у2))
                        Адресаты.Add(об_у2);
            }
        }

        return Адресаты;
    }

    private Объект НастройкиПроцессаТкп()
    {
        return НайтиОбъект("Настройки процессов ТКП РКД", "Наименование", "Процесс ТКП");
    }

    private bool ФлагОтправитьТолькоСпискуИзНастроекТкп()
    {
        bool ТолькоСписку = false;

        Объект НастройкиПроцесса = НастройкиПроцессаТкп();

        if (НастройкиПроцесса != null)
        {
            ТолькоСписку = НастройкиПроцесса.Параметр["Только списку"];
        }

        return ТолькоСписку;
    }

    private int МестоОтправкиИзНастроектПроцессаТкп()
    {
        int МестоОтправки = 0;

        Объект НастройкиПроцесса = НастройкиПроцессаТкп();

        if (НастройкиПроцесса != null)
        {
            МестоОтправки = НастройкиПроцесса.Параметр["Место отправки"];
        }

        return МестоОтправки;
    }

    private List<Объект> АдресатыУведомленийИзНастроекПроцессаТкп()
    {
        List<Объект> СписокПослеФильтра = new List<Объект>();

        Объект НастройкиПроцесса = НастройкиПроцессаТкп();

        if (НастройкиПроцесса != null)
        {
            List<Объект> Список = НастройкиПроцесса.СвязанныеОбъекты["Адресаты уведомлений"].ToList();

            if (Список.Count > 0)
                СписокПослеФильтра = ФильтрПоТипуПользователя(Список);
        }

        return СписокПослеФильтра;
    }

    private List<Объект> ФильтрАдресатов(List<Объект> АдресатыДоФильтра)
    {
        List<Объект> АдресатыПослеФильтра = new List<Объект>();

        if (АдресатыДоФильтра.Count > 0)
        {
            if (ФлагОтправитьТолькоСпискуИзНастроекТкп())
                АдресатыПослеФильтра = ФильтрПоТипуПользователя(АдресатыДоФильтра).Intersect(АдресатыУведомленийИзНастроекПроцессаТкп()).ToList();
            else
                АдресатыПослеФильтра = ФильтрПоТипуПользователя(АдресатыДоФильтра);
        }

        return АдресатыПослеФильтра;

        /*
        if (ФлагОтправитьТолькоСпискуИзНастроекТкп())
            return ФильтрПоТипуПользователя(АдресатыДоФильтра).Intersect(АдресатыУведомленийИзНастроекПроцессаТкп()).ToList();
        else
            return ФильтрПоТипуПользователя(АдресатыДоФильтра);
        */
    }

    private List<Объект> АдресатыЗадачиЭтапа(Объект Процесс, Объект Этап)
    {
        //Имена параметров и связей
        string _адресатыЭтапа = "Адресаты этапа";
        //string _наименование = "Наименование";
        string _планы = "Планы";
        string _этап = "Этап";
        string _исполнитель = "Исполнитель";
        string _этапОтветственного = "Этап Ответственного";
        string _ответственный = "Ответственный";

        List<Объект> АдресатыДоФильтра = new List<Объект>();

        if (Процесс != null)
        {
            //Объект Этап = Процесс.СвязанныйОбъект[_этап];

            if (Этап != null)
            {
                bool ЭтапОтв = Этап.Параметр[_этапОтветственного];

                if (ЭтапОтв)
                {
                    Объект Отв = Процесс.СвязанныйОбъект[_ответственный];

                    if (Отв != null)
                        АдресатыДоФильтра.Add(Отв);
                }

                else
                {
                    List<Объект> ПланыПроцесса = Процесс.СвязанныеОбъекты[_планы].ToList();

                    Объект План = ПланыПроцесса.FirstOrDefault(o => (ReferenceObject)o.СвязанныйОбъект[_этап] == (ReferenceObject)Этап); //Процесс.СвязанныйОбъект["Этап"]

                    //Объект План = ПланТекущий(Процесс);

                    if (План != null)
                    {
                        Объект ИсполнительПлана = План.СвязанныйОбъект[_исполнитель];

                        if (ИсполнительПлана != null)
                        {
                            АдресатыДоФильтра.Add(ИсполнительПлана);
                        }

                        else
                        {
                            АдресатыДоФильтра = Этап.СвязанныеОбъекты[_адресатыЭтапа].ToList();
                        }
                    }

                }
            }
        }

        return ФильтрАдресатов(АдресатыДоФильтра);
    }

    private List<Объект> АдресатыОкончанияПроцесса(Объект Процесс)
    {
        List<Объект> АдресатыДоФильтра = new List<Объект>();
        List<Объект> АдресатыПослеФильтра = new List<Объект>();

        if (Процесс != null)
        {
            Объект Отв = Процесс.СвязанныйОбъект["Ответственный"];

            if (Отв != null)
                АдресатыДоФильтра.Add(Отв);

        }

        if (АдресатыДоФильтра.Count > 0)
        {
            АдресатыПослеФильтра = ФильтрАдресатов(АдресатыДоФильтра);
        }
        //return АдресатыДоФильтра;
        return АдресатыПослеФильтра;


    }
}

public sealed class HandoffRecipient
{
    public int DocsId { get; set; }
    public string Name { get; set; }
    public string Email { get; set; }
}
public sealed class HandoffPacket
{
    public int Schema { get; set; }
    public string Mode { get; set; }
    public string RequestId { get; set; }
    public string CreatedUtc { get; set; }
    public string SourceMachine { get; set; }
    public int SourceDocsUserId { get; set; }
    public int ProcessReferenceId { get; set; }
    public int ProcessId { get; set; }
    public int StageId { get; set; }
    public string Title { get; set; }
    public string Kind { get; set; }
    public string TaskText { get; set; }
    public string Comment { get; set; }
    public string ProcessNameWithDate { get; set; }
    public string StageName { get; set; }
    public string ProcessUrl { get; set; }
    public string CardUrl { get; set; }
    public List<HandoffRecipient> Recipients { get; set; }
}
public sealed class HandoffEnvelope
{
    public string Payload { get; set; }
    public string Sha256 { get; set; }
}
internal static class HandoffWire
{
    internal const int MaxDataChars = 60000;
    internal static JavaScriptSerializer Serializer()
    {
        return new JavaScriptSerializer { MaxJsonLength = MaxDataChars, RecursionLimit = 16 };
    }
    internal static string Encode(HandoffPacket packet)
    {
        Validate(packet);
        string payload = Serializer().Serialize(packet);
        string data = Serializer().Serialize(new HandoffEnvelope { Payload = payload, Sha256 = Hash(payload) });
        if (data.Length > MaxDataChars) throw new InvalidOperationException("HANDOFF_PAYLOAD_TOO_LARGE");
        return data;
    }
    internal static HandoffPacket Decode(string data)
    {
        if (String.IsNullOrEmpty(data) || data.Length > MaxDataChars)
            throw new InvalidOperationException("HANDOFF_DATA_MISSING_OR_TOO_LARGE");
        HandoffEnvelope envelope;
        try { envelope = Serializer().Deserialize<HandoffEnvelope>(data); }
        catch (Exception) { throw new InvalidOperationException("INVALID_HANDOFF_ENVELOPE_JSON"); }
        if (envelope == null || String.IsNullOrEmpty(envelope.Payload) || envelope.Payload.Length > MaxDataChars
            || envelope.Sha256 == null || !String.Equals(Hash(envelope.Payload), envelope.Sha256, StringComparison.Ordinal))
            throw new InvalidOperationException("HANDOFF_PAYLOAD_HASH_MISMATCH");
        HandoffPacket packet;
        try { packet = Serializer().Deserialize<HandoffPacket>(envelope.Payload); }
        catch (Exception) { throw new InvalidOperationException("INVALID_HANDOFF_PACKET_JSON"); }
        Validate(packet);
        return packet;
    }
    internal static string Hash(string text)
    {
        using (var sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(text))).Replace("-", "").ToLowerInvariant();
    }
    internal static void Validate(HandoffPacket packet)
    {
        if (packet == null || !((packet.Schema == 1 && packet.Mode == "PREVIEW_ONLY")
            || (packet.Schema == 2 && packet.Mode == "SERVER_TEST_ONLY")))
            throw new InvalidOperationException("UNSUPPORTED_HANDOFF_SCHEMA_OR_MODE");
        Guid id;
        if (!Guid.TryParseExact(packet.RequestId, "N", out id) || id == Guid.Empty)
            throw new InvalidOperationException("INVALID_HANDOFF_REQUEST_ID");
        DateTime created;
        if (!DateTime.TryParseExact(packet.CreatedUtc, "O", CultureInfo.InvariantCulture,
            DateTimeStyles.RoundtripKind, out created) || created.Kind != DateTimeKind.Utc)
            throw new InvalidOperationException("INVALID_HANDOFF_CREATED_UTC");
        if (packet.SourceDocsUserId <= 0 || packet.ProcessReferenceId <= 0 || packet.ProcessId <= 0 || packet.StageId < 0)
            throw new InvalidOperationException("INVALID_HANDOFF_DOCS_ID");
        if (packet.Kind != "Задача" && packet.Kind != "Уведомление")
            throw new InvalidOperationException("INVALID_HANDOFF_KIND");
        CheckText(packet.SourceMachine, 128); CheckText(packet.Title, 2048);
        CheckText(packet.TaskText, 4096); CheckText(packet.Comment, 12000);
        CheckText(packet.ProcessNameWithDate, 4096); CheckText(packet.StageName, 2048);
        CheckOptionalDocsUrl(packet.ProcessUrl);
        CheckOptionalDocsUrl(packet.CardUrl);
        if (packet.Recipients == null || packet.Recipients.Count == 0 || packet.Recipients.Count > 200)
            throw new InvalidOperationException("HANDOFF_EXPECTS_1_TO_200_DOCS_RECIPIENTS");
        var ids = new HashSet<int>();
        foreach (HandoffRecipient recipient in packet.Recipients)
        {
            if (recipient == null || recipient.DocsId <= 0 || !ids.Add(recipient.DocsId))
                throw new InvalidOperationException("INVALID_OR_DUPLICATE_HANDOFF_RECIPIENT");
            CheckText(recipient.Name, 512); CheckText(recipient.Email, 512);
        }
    }
    private static void CheckOptionalDocsUrl(string value)
    {
        if (String.IsNullOrEmpty(value)) return;
        CheckText(value, 2048);
        Uri uri;
        if (!Uri.TryCreate(value, UriKind.Absolute, out uri) || uri.Scheme != "docs"
            || String.IsNullOrEmpty(uri.Host) || uri.UserInfo.Length != 0
            || value.IndexOf('\r') >= 0 || value.IndexOf('\n') >= 0)
            throw new InvalidOperationException("INVALID_HANDOFF_DOCS_URL");
    }
    private static void CheckText(string value, int max)
    {
        if (value == null || value.Length > max || value.IndexOf('\0') >= 0)
            throw new InvalidOperationException("HANDOFF_TEXT_MISSING_OR_TOO_LONG");
    }
}

internal static class HandoffServer
{
    internal static string Root
    {
        get
        {
            return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
                "TFlexDocs", "B24", "Server");
        }
    }

    internal static void RequireServer()
    {
        using (WindowsIdentity identity = WindowsIdentity.GetCurrent())
            if (identity.User == null )
                throw new B24ConfigFailure("SERVER_SYSTEM_ACCOUNT_REQUIRED");

        Type type = typeof(MacroContext).Assembly.GetType("TFlex.DOCs.Model.Macros.DynamicMacro", false);
        PropertyInfo property = type == null ? null : type.GetProperty("ExecutionPlace",
            BindingFlags.Public | BindingFlags.Static | BindingFlags.FlattenHierarchy);
        if (property == null)
            throw new B24ConfigFailure("EXECUTION_PLACE_API_UNAVAILABLE");
        object place;
        try { place = property.GetValue(null, null); }
        catch (Exception) { throw new B24ConfigFailure("EXECUTION_PLACE_READ_FAILED"); }
    }

    internal static void RequireProtectedDirectory(string path)
    {
        RequireNoReparsePoints(path);
        if (!Directory.Exists(path)) throw new B24ConfigFailure("SERVER_DIRECTORY_NOT_INITIALIZED");
        RequireAcl(Directory.GetAccessControl(path));
    }

    private static void RequireNoReparsePoints(string path)
    {
        string current = Path.GetFullPath(path);
        while (!String.IsNullOrEmpty(current))
        {
            if (File.Exists(current) || Directory.Exists(current))
                if ((File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
                    throw new B24ConfigFailure("REPARSE_POINT_NOT_ALLOWED");
            string parent = Path.GetDirectoryName(current);
            if (String.Equals(current, parent, StringComparison.OrdinalIgnoreCase)) break;
            current = parent;
        }
    }

    private static void RequireAcl(FileSystemSecurity security)
    {
        if (!security.AreAccessRulesProtected) throw new B24ConfigFailure("ACL_INHERITANCE_ENABLED");
        string owner = security.GetOwner(typeof(SecurityIdentifier)).Value;
        var seen = new HashSet<string>(StringComparer.Ordinal);
    }

    internal static string SafeCode(Exception ex)
    {
        var known = ex as B24ConfigFailure;
        if (known != null) return known.Code;
        if (ex is UnauthorizedAccessException) return "ACCESS_DENIED";
        if (ex is IOException) return "FILE_IO_FAILED";
        return "CONFIG_CHECK_ERROR";
    }
}

internal sealed class B24ConfigFailure : Exception
{
    internal readonly string Code;
    internal B24ConfigFailure(string code) : base(code) { Code = code; }
}


internal static class B24ServerStore
{
    internal static string Root { get { return HandoffServer.Root; } }
    internal static string ConfigPath { get { return Path.Combine(Root, "settings.json"); } }
    internal static void RequireServer() { HandoffServer.RequireServer(); }

    internal static Dictionary<string, object> Load()
    {
        RequireServer();
        RequireProtectedDirectory(Root);
        RequireNoReparsePoints(ConfigPath);
        if (!File.Exists(ConfigPath)) throw new B24ConfigFailure("CONFIG_NOT_FOUND_OR_NOT_ACCESSIBLE");
        RequireAcl(File.GetAccessControl(ConfigPath));
        string json;
        using (var stream = new FileStream(ConfigPath, FileMode.Open, FileAccess.Read, FileShare.Read))
        {
            if (stream.Length > 65536) throw new B24ConfigFailure("CONFIG_TOO_LARGE");
            using (var reader = new StreamReader(stream, Encoding.UTF8, true))
                json = reader.ReadToEnd();
        }
        Dictionary<string, object> settings;
        try
        {
            var serializer = new JavaScriptSerializer { MaxJsonLength = 65536, RecursionLimit = 16 };
            settings = serializer.DeserializeObject(json) as Dictionary<string, object>;
        }
        catch (Exception) { throw new B24ConfigFailure("INVALID_CONFIG_JSON"); }
        if (settings == null) throw new B24ConfigFailure("INVALID_CONFIG_JSON");
        var allowed = new HashSet<string>(new[] {
            "Enabled", "DryRun", "WebhookBaseUrl", "UserIdParameter", "ResolveByEmail",
            "RequestTimeoutSeconds", "BatchTimeoutSeconds", "MinRequestIntervalMs", "TestUserId",
            "UseAttachments", "ShowWarnings"
        }, StringComparer.Ordinal);
        foreach (string key in settings.Keys)
            if (!allowed.Contains(key)) throw new B24ConfigFailure("UNKNOWN_CONFIG_KEY");
        Boolean(settings, "Enabled");
        Boolean(settings, "DryRun");
        return settings;
    }

    internal static bool Boolean(Dictionary<string, object> settings, string key)
    {
        object value;
        if (!settings.TryGetValue(key, out value) || !(value is bool))
            throw new B24ConfigFailure("INVALID_REQUIRED_BOOLEAN");
        return (bool)value;
    }

    internal static void RequireProtectedDirectory(string path)
    {
        RequireNoReparsePoints(path);
        if (!Directory.Exists(path)) throw new B24ConfigFailure("SERVER_DIRECTORY_NOT_INITIALIZED");
        RequireAcl(Directory.GetAccessControl(path));
    }

    private static void RequireNoReparsePoints(string path)
    {
        string current = Path.GetFullPath(path);
        while (!String.IsNullOrEmpty(current))
        {
            if (File.Exists(current) || Directory.Exists(current))
                if ((File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
                    throw new B24ConfigFailure("REPARSE_POINT_NOT_ALLOWED");
            string parent = Path.GetDirectoryName(current);
            if (String.Equals(current, parent, StringComparison.OrdinalIgnoreCase)) break;
            current = parent;
        }
    }

    private static void RequireAcl(FileSystemSecurity security)
    {
        if (!security.AreAccessRulesProtected) throw new B24ConfigFailure("ACL_INHERITANCE_ENABLED");
        string owner = security.GetOwner(typeof(SecurityIdentifier)).Value;
        var seen = new HashSet<string>(StringComparer.Ordinal);
    }

    internal static string SafeCode(Exception ex)
    {
        var known = ex as B24ConfigFailure;
        if (known != null) return known.Code;
        if (ex is UnauthorizedAccessException) return "ACCESS_DENIED";
        if (ex is IOException) return "FILE_IO_FAILED";
        return "CONFIG_CHECK_ERROR";
    }
}



public sealed class B24Settings
{
    public bool Enabled { get; set; }
    public bool DryRun { get; set; }
    public string WebhookBaseUrl { get; set; }
    public string UserIdParameter { get; set; }
    public bool ResolveByEmail { get; set; }
    public int RequestTimeoutSeconds { get; set; }
    public int BatchTimeoutSeconds { get; set; }
    public int MinRequestIntervalMs { get; set; }
    public long TestUserId { get; set; }
    public bool UseAttachments { get; set; }
    public bool ShowWarnings { get; set; }

    public B24Settings()
    {
        Enabled = false;
        DryRun = true;
        WebhookBaseUrl = "";
        UserIdParameter = "";
        ResolveByEmail = true;
        RequestTimeoutSeconds = 8;
        BatchTimeoutSeconds = 30;
        MinRequestIntervalMs = 600;
        TestUserId = 0;
        UseAttachments = true;
        ShowWarnings = true;
    }

    public static string ConfigPath() { return B24ServerStore.ConfigPath; }
    public static B24Settings Load()
    {
        Dictionary<string, object> values = B24ServerStore.Load();
        try { return B24Json.Serializer().Deserialize<B24Settings>(B24Json.Serializer().Serialize(values)); }
        catch (Exception) { throw new B24Failure("INVALID_CONFIG_VALUE", false, true); }
    }

    public void ValidateForApi()
    {
        Uri uri;
        if (!Uri.TryCreate(WebhookBaseUrl, UriKind.Absolute, out uri)
            || uri.Scheme != Uri.UriSchemeHttps || uri.UserInfo.Length != 0
            || uri.Query.Length != 0 || uri.Fragment.Length != 0
            || !Regex.IsMatch(uri.AbsolutePath, @"^/rest/[1-9][0-9]*/[A-Za-z0-9_-]+/$")
            || uri.AbsolutePath.Contains("REPLACE"))
            throw new B24Failure("INVALID_WEBHOOK_BASE_URL", false, true);
        if (RequestTimeoutSeconds < 1 || RequestTimeoutSeconds > 60
            || BatchTimeoutSeconds < RequestTimeoutSeconds || BatchTimeoutSeconds > 300
            || MinRequestIntervalMs < 0 || MinRequestIntervalMs > 10000)
            throw new B24Failure("INVALID_TIMEOUT_SETTINGS", false, true);
        if (!ResolveByEmail && String.IsNullOrWhiteSpace(UserIdParameter) && TestUserId <= 0)
            throw new B24Failure("NO_RECIPIENT_RESOLUTION_CONFIGURED", false, true);
    }
}

public static class B24Json
{
    public static JavaScriptSerializer Serializer()
    {
        return new JavaScriptSerializer { MaxJsonLength = 1048576, RecursionLimit = 32 };
    }
    public static string Text(object value)
    {
        return value == null ? "" : Convert.ToString(value, CultureInfo.InvariantCulture);
    }
    public static object Get(Dictionary<string, object> data, string name)
    {
        object value;
        return data != null && data.TryGetValue(name, out value) ? value : null;
    }
    public static long PositiveId(object value)
    {
        long id;
        return Int64.TryParse(Text(value), NumberStyles.None, CultureInfo.InvariantCulture, out id) && id > 0 ? id : 0;
    }
    public static bool IsTrue(object value)
    {
        string text = Text(value);
        return text.Equals("true", StringComparison.OrdinalIgnoreCase)
            || text.Equals("Y", StringComparison.OrdinalIgnoreCase) || text == "1";
    }
}

public sealed class B24MessageBuilder
{
    private readonly string _title;
    private readonly List<object> _blocks = new List<object>();
    private readonly List<string> _plain = new List<string>();

    public B24MessageBuilder(string title) { _title = title ?? ""; }

    public static string EscapeText(string text)
    {
        return (text ?? "").Replace("[", "［").Replace("]", "］");
    }

    public void AddMessage(string message)
    {
        _blocks.Add(new Dictionary<string, object> { { "MESSAGE", EscapeText(message) } });
        _plain.Add(message ?? "");
    }

    public void AddGrid(IEnumerable<KeyValuePair<string, string>> fields)
    {
        List<object> grid = new List<object>();
        foreach (KeyValuePair<string, string> pair in fields)
        {
            grid.Add(new Dictionary<string, object> {
                { "NAME", EscapeText(pair.Key) }, { "VALUE", EscapeText(pair.Value) }, { "DISPLAY", "LINE" }
            });
            _plain.Add(pair.Key + ": " + pair.Value);
        }
        if (grid.Count > 0) _blocks.Add(new Dictionary<string, object> { { "GRID", grid } });
    }

    public void AddDelimiter()
    {
        _blocks.Add(new Dictionary<string, object> {
            { "DELIMITER", new Dictionary<string, object> { { "SIZE", 400 }, { "COLOR", "#ffffff" } } }
        });
    }

    public void AddLink(string name, string url)
    {
        Uri uri;
        if (Uri.TryCreate(url, UriKind.Absolute, out uri)
            && (uri.Scheme == Uri.UriSchemeHttp || uri.Scheme == Uri.UriSchemeHttps))
        {
            _blocks.Add(new Dictionary<string, object> {
                { "LINK", new Dictionary<string, object> { { "NAME", EscapeText(name) }, { "LINK", url } } }
            });
            _plain.Add(name + ": " + url);
        }
        else
        {
            AddMessage(name + ":\n" + url);
        }
    }

    public Dictionary<string, object> Build(long userId, bool useAttachments)
    {
        if (userId <= 0) throw new B24Failure("INVALID_DIALOG_ID", false, true);
        string message = "[B]" + EscapeText(_title) + "[/B]";
        if (!useAttachments && _plain.Count > 0) message += "\n\n" + EscapeText(String.Join("\n", _plain));
        Dictionary<string, object> payload = new Dictionary<string, object> {
 //           { "DIALOG_ID", userId.ToString(CultureInfo.InvariantCulture) },
             { "DIALOG_ID", "chat78766" },
            { "MESSAGE", message }, { "URL_PREVIEW", "N" }
        };
        if (useAttachments && _blocks.Count > 0) payload.Add("ATTACH", _blocks);
        if (Encoding.UTF8.GetByteCount(B24Json.Serializer().Serialize(payload)) > 65536)
            throw new B24Failure("PAYLOAD_EXCEEDS_LOCAL_64K_LIMIT", false, true);
        return payload;
    }
}

public sealed class B24Recipient
{
    public int DocsId;
    public string Name;
    public string Email;
    public long ExplicitUserId;
    public string PreparationError;
}

public sealed class B24DeliveryItem
{
    public B24Recipient Recipient;
    public string Status;
    public long B24UserId;
    public long MessageId;
    public string Code;
}

public sealed class B24RunResult
{
    public string RunId;
    public readonly List<B24DeliveryItem> Items = new List<B24DeliveryItem>();
    public bool HasProblems { get { return Items.Any(i => i.Status != "SENT" && i.Status != "DRY_RUN" && i.Status != "DUPLICATE"); } }
    public string Summary()
    {
        StringBuilder text = new StringBuilder();
        if (!String.IsNullOrEmpty(RunId)) text.AppendLine("Операция: " + RunId);
        if (Items.Count == 0) text.AppendLine("После фильтрации адресатов нет.");
        foreach (IGrouping<string, B24DeliveryItem> group in Items.GroupBy(i => i.Status))
            text.AppendLine(group.Key + ": " + group.Count());
        text.AppendLine();
        foreach (B24DeliveryItem item in Items.Take(40))
            text.AppendLine("DOCs ID=" + item.Recipient.DocsId + " " + item.Recipient.Name
                + " -> Б24 ID=" + item.B24UserId + ": " + item.Status
                + (item.MessageId > 0 ? "; message_id=" + item.MessageId : "")
                + (String.IsNullOrEmpty(item.Code) ? "" : "; " + item.Code));
        if (Items.Count > 40) text.AppendLine("Остальные результаты — в журнале.");
        text.AppendLine("\nЖурнал: " + B24Journal.CurrentPath());
        text.AppendLine("DRY_RUN = проверка без отправки. UNKNOWN = исход отправки неизвестен; не повторять вслепую.");
        return text.ToString();
    }
}

public sealed class B24Failure : Exception
{
    public readonly string Code;
    public readonly bool Uncertain;
    public readonly bool StopBatch;
    public B24Failure(string code, bool uncertain, bool stopBatch) : base(code)
    {
        Code = code; Uncertain = uncertain; StopBatch = stopBatch;
    }
    public static string SafeCode(Exception ex)
    {
        B24Failure known = ex as B24Failure;
        return known == null ? "INTERNAL_" + ex.GetType().Name : known.Code;
    }
}

public interface IB24Api
{
    Dictionary<string, object> Call(string method, Dictionary<string, object> arguments);
}

public sealed class B24RestClient : IB24Api, IDisposable
{
    private readonly B24Settings _settings;
    private readonly HttpClient _http;
    private readonly Stopwatch _clock = Stopwatch.StartNew();
    private long _lastStart = -1;

    public B24RestClient(B24Settings settings) : this(settings,
        new HttpClientHandler { AllowAutoRedirect = false, UseCookies = false,
            UseDefaultCredentials = false, Credentials = null }) { }

    public B24RestClient(B24Settings settings, HttpMessageHandler handler)
    {
        settings.ValidateForApi();
        _settings = settings;
        _http = new HttpClient(handler, true);
        _http.Timeout = TimeSpan.FromSeconds(settings.RequestTimeoutSeconds);
        _http.MaxResponseContentBufferSize = 1048576;
    }

    public Dictionary<string, object> Call(string method, Dictionary<string, object> arguments)
    {
        if (method != "user.get" && method != "im.message.add")
            throw new B24Failure("METHOD_NOT_ALLOWED", false, true);
        bool write = method == "im.message.add";
        int pause = _lastStart < 0 ? 0 : (int)Math.Max(0, _settings.MinRequestIntervalMs - (_clock.ElapsedMilliseconds - _lastStart));
        long remaining = _settings.BatchTimeoutSeconds * 1000L - _clock.ElapsedMilliseconds;
        if (remaining <= pause) throw new B24Failure("BATCH_BUDGET_EXHAUSTED", false, true);
        if (pause > 0) Thread.Sleep(pause);
        remaining = _settings.BatchTimeoutSeconds * 1000L - _clock.ElapsedMilliseconds;
        if (remaining <= 0) throw new B24Failure("BATCH_BUDGET_EXHAUSTED", false, true);
        _lastStart = _clock.ElapsedMilliseconds;

        using (CancellationTokenSource cancellation = new CancellationTokenSource())
        using (HttpRequestMessage request = new HttpRequestMessage(HttpMethod.Post,
            new Uri(new Uri(_settings.WebhookBaseUrl), method + ".json")))
        {
            cancellation.CancelAfter(TimeSpan.FromMilliseconds(remaining));
            request.Content = new StringContent(B24Json.Serializer().Serialize(arguments), Encoding.UTF8, "application/json");
            request.Headers.Accept.ParseAdd("application/json");
            try
            {
                using (HttpResponseMessage response = _http.SendAsync(request,
                    HttpCompletionOption.ResponseContentRead, cancellation.Token).GetAwaiter().GetResult())
                {
                    string body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
                    Dictionary<string, object> parsed = null;
                    try { parsed = B24Json.Serializer().DeserializeObject(body) as Dictionary<string, object>; }
                    catch (Exception) { /* Ни HTML, ни сырое тело ответа в журнал не попадают. */ }
                    string apiError = B24Json.Text(B24Json.Get(parsed, "error"));
                    int status = (int)response.StatusCode;
                    if (!response.IsSuccessStatusCode || (parsed != null && parsed.ContainsKey("error")))
                    {
                        string safe = Regex.IsMatch(apiError, @"^[A-Za-z0-9_]{1,80}$") ? apiError : "UNSPECIFIED";
                        throw new B24Failure("HTTP_" + status + "/" + safe, write && status >= 500, true);
                    }
                    if (parsed == null || !parsed.ContainsKey("result"))
                        throw new B24Failure("INVALID_REST_RESPONSE", write, true);
                    return parsed;
                }
            }
            catch (OperationCanceledException) { throw new B24Failure("REQUEST_TIMEOUT", write, true); }
            catch (HttpRequestException) { throw new B24Failure("TRANSPORT_ERROR", write, true); }
        }
    }

    public void Dispose() { _http.Dispose(); }
}

public sealed class B24DeliveryService
{
    private readonly IB24Api _api;
    private readonly B24Settings _settings;
    public B24DeliveryService(IB24Api api, B24Settings settings) { _api = api; _settings = settings; }

    public B24RunResult Run(IEnumerable<B24Recipient> recipients, B24MessageBuilder builder,
        bool dryRun, Action<B24DeliveryItem> journal)
    {
        B24RunResult result = new B24RunResult();
        HashSet<long> attempted = new HashSet<long>();
        Dictionary<string, long> resolved = new Dictionary<string, long>(StringComparer.OrdinalIgnoreCase);
        bool stopped = false;
        foreach (B24Recipient recipient in recipients)
        {
            B24DeliveryItem item = new B24DeliveryItem { Recipient = recipient, Status = "NOT_ATTEMPTED", Code = "" };
            bool requestStarted = false;
            try
            {
                if (stopped) { item.Code = "BATCH_STOPPED"; }
                else if (!String.IsNullOrEmpty(recipient.PreparationError))
                { item.Status = "SKIPPED"; item.Code = recipient.PreparationError; }
                else
                {
                    string cacheKey = recipient.ExplicitUserId > 0
                        ? "id:" + recipient.ExplicitUserId : "email:" + (recipient.Email ?? "").Trim();
                    long userId;
                    if (!resolved.TryGetValue(cacheKey, out userId))
                    {
                        userId = Resolve(recipient);
                        resolved[cacheKey] = userId;
                    }
                    item.B24UserId = userId;
                    if (!attempted.Add(userId))
                    { item.Status = "DUPLICATE"; item.Code = "SAME_B24_USER_IN_THIS_CALL"; }
                    else if (dryRun) item.Status = "DRY_RUN";
                    else
                    {
                        Dictionary<string, object> payload = builder.Build(userId, _settings.UseAttachments);
                        journal(new B24DeliveryItem { Recipient = recipient, B24UserId = userId, Status = "ATTEMPT", Code = "" });
                        requestStarted = true;
                        Dictionary<string, object> response = _api.Call("im.message.add", payload);
                        long messageId = B24Json.PositiveId(B24Json.Get(response, "result"));
                        if (messageId == 0) throw new B24Failure("INVALID_MESSAGE_ID_IN_RESPONSE", true, true);
                        item.MessageId = messageId;
                        item.Status = "SENT";
                    }
                }
            }
            catch (B24Failure ex)
            {
                item.Status = ex.Uncertain ? "UNKNOWN" : (ex.StopBatch ? "FAILED" : "SKIPPED");
                item.Code = ex.Code;
                stopped = stopped || ex.StopBatch;
            }
            catch (Exception ex)
            {
                item.Status = requestStarted ? "UNKNOWN" : "FAILED";
                item.Code = B24Failure.SafeCode(ex);
                stopped = true;
            }
            result.Items.Add(item);
            try { journal(item); }
            catch (Exception)
            {
                item.Code += "; LOG_WRITE_FAILED";
                stopped = true;
                if (item.Status == "SENT") item.Status = "SENT_LOG_FAILED";
                else if (item.Status == "DRY_RUN" || item.Status == "DUPLICATE") item.Status = "FAILED";
            }
        }
        return result;
    }

    public long Resolve(B24Recipient recipient)
    {
        Dictionary<string, object> filter = new Dictionary<string, object> { { "ACTIVE", true } };
        string email = (recipient.Email ?? "").Trim();
        if (recipient.ExplicitUserId > 0) filter.Add("ID", recipient.ExplicitUserId);
        else
        {
            if (!_settings.ResolveByEmail) throw new B24Failure("EMAIL_LOOKUP_DISABLED", false, false);
            if (email.Length == 0) throw new B24Failure("EMPTY_EMAIL", false, false);
            try
            {
                System.Net.Mail.MailAddress address = new System.Net.Mail.MailAddress(email);
                if (!address.Address.Equals(email, StringComparison.OrdinalIgnoreCase))
                    throw new FormatException();
            }
            catch (Exception) { throw new B24Failure("INVALID_EMAIL", false, false); }
            filter.Add("=EMAIL", email);
        }
        Dictionary<string, object> response = _api.Call("user.get", new Dictionary<string, object> { { "FILTER", filter } });
        object raw = B24Json.Get(response, "result");
        IEnumerable rows = raw as IEnumerable;
        if (rows == null || raw is string || raw is IDictionary)
            throw new B24Failure("INVALID_USER_RESPONSE", false, true);
        object next = B24Json.Get(response, "next");
        if (next != null && !(next is bool && (bool)next == false))
            throw new B24Failure("USER_RESULT_PAGED_CHECK_MATCHING", false, false);
        HashSet<long> matches = new HashSet<long>();
        foreach (object row in rows)
        {
            Dictionary<string, object> user = row as Dictionary<string, object>;
            if (user == null) throw new B24Failure("INVALID_USER_RESPONSE", false, true);
            long id = B24Json.PositiveId(B24Json.Get(user, "ID"));
            if (id == 0 || !B24Json.IsTrue(B24Json.Get(user, "ACTIVE"))) continue;
            if (recipient.ExplicitUserId > 0 ? id == recipient.ExplicitUserId
                : B24Json.Text(B24Json.Get(user, "EMAIL")).Trim().Equals(email, StringComparison.OrdinalIgnoreCase))
                matches.Add(id);
        }
        if (matches.Count == 0) throw new B24Failure("ACTIVE_USER_NOT_FOUND", false, false);
        if (matches.Count != 1) throw new B24Failure("AMBIGUOUS_USER_MATCH", false, false);
        return matches.First();
    }
}


internal static class B24TestPolicy
{
    internal static B24RunResult Execute(HandoffPacket packet, B24Settings settings,
        IB24Api api, Action<B24DeliveryItem> journal)
    {
        HandoffWire.Validate(packet);
        if (packet.Schema != 2 || packet.Mode != "SERVER_TEST_ONLY")
            throw new B24Failure("TEST_PACKET_REQUIRED_NO_PREVIEW_REPLAY", false, true);
        if (settings.TestUserId <= 0)
            throw new B24Failure("TEST_USER_ID_REQUIRED", false, true);
        DateTime created = DateTime.ParseExact(packet.CreatedUtc, "O", CultureInfo.InvariantCulture,
            DateTimeStyles.RoundtripKind);
        TimeSpan age = DateTime.UtcNow - created;
        if (age > TimeSpan.FromHours(24) || age < TimeSpan.FromMinutes(-5))
            throw new B24Failure("TEST_PACKET_EXPIRED_OR_FUTURE", false, true);
        settings.ValidateForApi();
        B24MessageBuilder builder = BuildMessage(packet);
        builder.Build(settings.TestUserId, settings.UseAttachments);
        var recipients = new[] { new B24Recipient {
            DocsId = 0, Name = "Тестовый адресат из серверного конфига",
            ExplicitUserId = settings.TestUserId
        } };
        return new B24DeliveryService(api, settings).Run(recipients, builder, settings.DryRun, journal);
    }

    internal static B24MessageBuilder BuildMessage(HandoffPacket p)
    {
        var builder = new B24MessageBuilder("ТЕСТ ДОСТАВКИ / " + p.Title);
        builder.AddMessage("Административная проверка канала DOCs → Б24. Это не новое задание сотруднику.");
        builder.AddMessage(p.Kind + ": " + p.TaskText);
        builder.AddMessage("Комментарий: " + p.Comment);
        var fields = new List<KeyValuePair<string, string>> {
            new KeyValuePair<string, string>("Процесс", p.ProcessNameWithDate)
        };
        if (!String.IsNullOrEmpty(p.StageName))
            fields.Add(new KeyValuePair<string, string>("Этап", p.StageName));
        builder.AddGrid(fields);
        builder.AddDelimiter();
        if (!String.IsNullOrEmpty(p.ProcessUrl)) builder.AddLink("Ссылка на Процесс", p.ProcessUrl);
        if (!String.IsNullOrEmpty(p.CardUrl)) builder.AddLink("Ссылка на Карточку проекта", p.CardUrl);
        builder.AddMessage("RequestId: " + p.RequestId);
        return builder;
    }
}

internal static class B24TestOnce
{
    internal static string Mark(string directory, string requestId, long userId)
    {
        Guid id;
        if (!Guid.TryParseExact(requestId, "N", out id) || id == Guid.Empty || userId <= 0)
            throw new B24Failure("INVALID_TEST_ATTEMPT_KEY", false, true);
        string path = Path.Combine(directory, "send-test-" + id.ToString("N") + ".attempt");
        try
        {
            using (var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                byte[] bytes = Encoding.UTF8.GetBytes("RequestId=" + id.ToString("N")
                    + "\nTestUserId=" + userId.ToString(CultureInfo.InvariantCulture)
                    + "\nAttemptReservedUtc=" + DateTime.UtcNow.ToString("O")
                    + "\nNot proof of delivery. Do not remove to retry.\n");
                stream.Write(bytes, 0, bytes.Length);
                stream.Flush(true);
            }
            return path;
        }
        catch (IOException)
        {
            if (File.Exists(path)) throw new B24Failure("TEST_ALREADY_ATTEMPTED", false, true);
            throw new B24Failure("TEST_ATTEMPT_MARK_FAILED", false, true);
        }
        catch (Exception) { throw new B24Failure("TEST_ATTEMPT_MARK_FAILED", false, true); }
    }
}

internal static class B24ServerTest
{
    internal static void Run(HandoffPacket packet, string taskId)
    {
        HandoffServer.RequireServer();
        HandoffServer.RequireProtectedDirectory(HandoffServer.Root);
        string reports = Path.Combine(HandoffServer.Root, "Reports");
        string logs = Path.Combine(HandoffServer.Root, "Logs");
        HandoffServer.RequireProtectedDirectory(reports);
        HandoffServer.RequireProtectedDirectory(logs);
        var report = new StringBuilder();
        report.AppendLine("TFLEX DOCs / Б24: тест серверной доставки");
        report.AppendLine("Редакция: SERVER_TEST_1");
        report.AppendLine("UTC: " + DateTime.UtcNow.ToString("O"));
        report.AppendLine("Компьютер: " + Environment.MachineName);
        report.AppendLine("Процесс: TFlex.DOCs.EventService");
        report.AppendLine("Задача DOCs: " + taskId);
        report.AppendLine("RequestId: " + packet.RequestId);
        report.AppendLine("Режим: SERVER_TEST_ONLY; адресат только TestUserId из конфигурации");
        report.AppendLine("Получателей в исходном снимке: " + packet.Recipients.Count);
        report.AppendLine("Список исходных адресатов не используется для отправки.");
        string outcome = "TEST_FAILED";
        string failure = null;
        try
        {
            B24Settings settings = B24Settings.Load();
            report.AppendLine("Enabled=" + settings.Enabled + "; DryRun=" + settings.DryRun);
            report.AppendLine("Enabled не включает рабочую рассылку: это явный административный тест.");
            if (settings.TestUserId <= 0)
                throw new B24Failure("TEST_USER_ID_REQUIRED", false, true);
            settings.ValidateForApi();
            report.AppendLine("TestUserId Б24: " + settings.TestUserId);
            B24Journal.Write(packet.RequestId, packet.ProcessId, null, "BEGIN_TEST", settings.TestUserId, 0,
                settings.DryRun ? "DRY_RUN" : "SEND_TEST");
            using (var api = new B24RestClient(settings))
            {
                B24RunResult result = B24TestPolicy.Execute(packet, settings, api,
                    delegate(B24DeliveryItem item)
                    {
                        if (item.Status == "ATTEMPT")
                            B24TestOnce.Mark(logs, packet.RequestId, item.B24UserId);
                        B24Journal.Write(packet.RequestId, packet.ProcessId, item.Recipient,
                            item.Status, item.B24UserId, item.MessageId, item.Code);
                    });
                B24DeliveryItem item = result.Items.Single();
                outcome = item.Status == "SENT" ? "TEST_SENT"
                    : item.Status == "DRY_RUN" ? "TEST_DRY_RUN"
                    : item.Code == "TEST_ALREADY_ATTEMPTED" ? "TEST_ALREADY_ATTEMPTED"
                    : item.Status == "UNKNOWN" ? "TEST_UNKNOWN" : "TEST_FAILED";
                report.AppendLine("Статус адресата: " + item.Status);
                report.AppendLine("Б24 ID: " + item.B24UserId);
                report.AppendLine("MessageId: " + item.MessageId);
                report.AppendLine("Код: " + item.Code);
                if (outcome != "TEST_SENT" && outcome != "TEST_DRY_RUN") failure = outcome;
            }
        }
        catch (Exception ex)
        {
            failure = SafeError(ex);
            report.AppendLine("Код: " + failure);
            try { B24Journal.Write(packet.RequestId, packet.ProcessId, null, "FAILED", 0, 0, failure); }
            catch (Exception) { report.AppendLine("Запись ошибки в журнал не удалась."); }
        }
        report.AppendLine("Результат: " + outcome);
        report.AppendLine("Почтовых сообщений: 0. Данные процесса и действий не изменялись.");
        report.AppendLine("Журнал: " + B24Journal.CurrentPath());
        string path = Path.Combine(reports, "b24-test-" + packet.RequestId + "-"
            + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-fff") + "-" + Guid.NewGuid().ToString("N") + ".txt");
        try
        {
            using (var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
            using (var writer = new StreamWriter(stream, new UTF8Encoding(true))) writer.Write(report.ToString());
        }
        catch (Exception) { throw new InvalidOperationException("SERVER_TEST_REPORT_WRITE_FAILED_CHECK_JOURNAL_NO_RETRY"); }
        if (failure != null)
            throw new InvalidOperationException("B24_SERVER_TEST_FAILED; code=" + failure + "; report=" + path);
    }

    private static string SafeError(Exception ex)
    {
        var config = ex as B24ConfigFailure;
        if (config != null) return config.Code;
        return B24Failure.SafeCode(ex);
    }
}

public static class B24Journal
{
    private static readonly object Gate = new object();
    public static string CurrentPath()
    {
        return Path.Combine(HandoffServer.Root, "Logs", DateTime.UtcNow.ToString("yyyy-MM-dd")
            + "-" + Process.GetCurrentProcess().Id + ".jsonl");
    }
    public static void Write(string runId, int processId, B24Recipient recipient, string status,
        long userId, long messageId, string code)
    {
        HandoffServer.RequireServer();
        HandoffServer.RequireProtectedDirectory(Path.Combine(HandoffServer.Root, "Logs"));
        var row = new Dictionary<string, object> {
            { "utc", DateTime.UtcNow.ToString("O") }, { "request_id", runId },
            { "machine", Environment.MachineName }, { "pid", Process.GetCurrentProcess().Id },
            { "process_id", processId }, { "docs_user_id", recipient == null ? 0 : recipient.DocsId },
            { "b24_user_id", userId }, { "status", status }, { "message_id", messageId }, { "code", code ?? "" }
        };
        byte[] bytes = new UTF8Encoding(false).GetBytes(B24Json.Serializer().Serialize(row) + Environment.NewLine);
        lock (Gate)
        {
            using (var stream = new FileStream(CurrentPath(), FileMode.Append, FileAccess.Write, FileShare.Read))
            {
                stream.Write(bytes, 0, bytes.Length);
                stream.Flush(true);
            }
        }
    }
}
