// TFlex.DOCs.DatabaseObjects, Version=17.4.2.0, Culture=neutral, PublicKeyToken=null
// TFlex.DOCs.DatabaseObjects.ClientSessionData
using System;
using System.Collections.Generic;
using System.Data.SqlClient;
using System.Diagnostics;
using System.IO;
using System.Linq;
using TFlex.DOCs.Common;
using TFlex.DOCs.Common.Encryption;
using TFlex.DOCs.Database;
using TFlex.DOCs.Database.Select;
using TFlex.DOCs.DatabaseObjects;
using TFlex.DOCs.DatabaseObjects.Gateways;
using TFlex.DOCs.RPC.Server;
using TFlex.DOCs.RPC.Services;
using TFlex.DOCs.Server.DatabaseObjects;

[DebuggerDisplay("ClientSessionData: System:{IsSystem}; User:{UserFullName}(ID:{UserId}); Host:{HostId}; ConfigurationId:{ConfigurationId}")]
public sealed class ClientSessionData : IDisposable
{
	private static string _administratorFullName = "Администратор";

	private static bool _administratorFullNameInit;

	private volatile bool _disposed;

	private Dictionary<string, ServiceServer> _clientCallbacks;

	public CertificateSessionItemsCollection Certificates { get; private set; }

	public Guid SessionGuid { get; } = Guid.NewGuid();

	public int UserId { get; }

	public Guid UserGuid { get; }

	public string UserFullName { get; }

	public string IpAddress { get; }

	public int HostId { get; }

	public int AccessLevel { get; }

	public int ClientViewId { get; }

	public int ConfigurationId { get; set; }

	public List<IProductUsage> Products { get; set; }

	public bool IsSystem => UserId == UsersGateway.SystemUserId;

	public UserAccessInfo Access { get; }

	public List<string> TemporaryFiles { get; set; }

	public bool UseTransactions { get; set; }

	public bool NormalShutdown { get; set; }

	public bool OpenSuccessfully { get; set; }

	public bool UseSessionLog { get; set; } = true;

	public bool IsDisposed => _disposed;

	public static void InitAdministratorFullName(DatabaseGateway databaseGateway)
	{
		if (_administratorFullNameInit)
		{
			return;
		}
		try
		{
			_administratorFullName = SelectQueryBuilder.Create(new ParameterGroupsGateway(databaseGateway, null).GetParameterGroup(SystemParameterGroups.Users), databaseGateway).First().AddField(Fields.Users.FullName)
				.WithTerm(Fields.Users.s_Guid, "=", databaseGateway.Escape(SystemObjects.AdiministratorObject))
				.ExecuteScalar<string>();
		}
		catch (SqlException)
		{
		}
		finally
		{
			_administratorFullNameInit = true;
		}
	}

	public ClientSessionData(int userId, Guid userGuid, string userFullName, string ipAddress, int hostId, int clientViewId, int accessLevelId, DatabaseGateway database)
	{
		UserId = userId;
		UserGuid = userGuid;
		UserFullName = userFullName;
		IpAddress = ipAddress;
		HostId = hostId;
		AccessLevel = accessLevelId;
		ClientViewId = clientViewId;
		UseTransactions = true;
		Access = new UserAccessInfo();
		Access.Initialize(this, database);
		if (database != null)
		{
			database.Certificates.Certificates = Certificates;
		}
		DatabaseGatewayCertificates.ClearCommonCertificates();
	}

	public ClientSessionData(ClientSessionData source, int userId, Guid userGuid)
	{
		UserId = userId;
		UserGuid = userGuid;
		HostId = source.HostId;
		AccessLevel = source.AccessLevel;
		ClientViewId = source.ClientViewId;
		UseTransactions = source.UseTransactions;
		Access = source.Access;
		DatabaseGatewayCertificates.SetCommonCertificates(Certificates);
		_clientCallbacks = source._clientCallbacks;
	}

	public void Dispose()
	{
		if (!_disposed)
		{
			_disposed = true;
			if (TemporaryFiles == null)
			{
				return;
			}
			foreach (string temporaryFile in TemporaryFiles)
			{
				try
				{
					File.Delete(temporaryFile);
				}
				catch
				{
				}
			}
			TemporaryFiles = null;
		}
		GC.SuppressFinalize(this);
	}

	public static ClientSessionData CreateAdministratorSession(DatabaseGateway databaseGateway)
	{
		return new ClientSessionData(1, SystemObjects.AdiministratorObject, _administratorFullName, "localhost", 0, 0, 0, databaseGateway);
	}

	public static ClientSessionData CreateLightweightAdministratorSession()
	{
		return new ClientSessionData(1, SystemObjects.AdiministratorObject, _administratorFullName, "localhost", 0, 0, 0, null);
	}

	public void AddTemporaryFile(string filePath)
	{
		if (TemporaryFiles == null)
		{
			TemporaryFiles = new List<string>();
		}
		TemporaryFiles.Add(filePath.ToLower());
	}

	public void DeleteTemporaryFile(string filePath)
	{
		try
		{
			if (File.Exists(filePath))
			{
				File.Delete(filePath);
			}
		}
		catch
		{
		}
		if (TemporaryFiles != null && TemporaryFiles.Remove(filePath.ToLower()) && TemporaryFiles.Count == 0)
		{
			TemporaryFiles = null;
		}
	}

	public CertificateSessionItem GetCertificate(Guid certificateGuid)
	{
		return Certificates?.GetCertificate(certificateGuid);
	}

	public void RemoveCertificate(Guid certificateGuid)
	{
		if (Certificates != null && Certificates.ContainsKey(certificateGuid))
		{
			Certificates.Remove(certificateGuid);
		}
	}

	public void ApplyCertificates(CertificateSessionItemsCollection certificates)
	{
		if (certificates.IsNullOrEmpty())
		{
			Certificates = null;
		}
		else if (Certificates == null)
		{
			Certificates = new CertificateSessionItemsCollection(certificates);
		}
		else
		{
			Certificates.Assign(certificates);
		}
	}

	public string SetApplicationServerCallback(ServiceServer server, ServerCallContext context)
	{
		if (server != null)
		{
			if (_clientCallbacks == null)
			{
				_clientCallbacks = new Dictionary<string, ServiceServer>();
			}
			_clientCallbacks[context.SessionId] = server;
		}
		return context.SessionId;
	}

	public void RemoveApplicationServerCallback(string internalSessionId)
	{
		_clientCallbacks?.Remove(internalSessionId);
	}

	public IReadOnlyCollection<ServiceServer> GetAssociatedCallbacks()
	{
		return _clientCallbacks?.Values.ToArray() ?? Array.Empty<ServiceServer>();
	}
}
