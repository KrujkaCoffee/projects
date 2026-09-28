// TFlex.DOCs.RPC, Version=17.4.2.0, Culture=neutral, PublicKeyToken=null
// TFlex.DOCs.RPC.Server.ServerCallContext
using System;
using System.Security.Principal;
using System.Threading;

public abstract class ServerCallContext : IDisposable
{
	public abstract string SessionId { get; }

	public string OperationName { get; }

	public abstract TimeSpan OperationTimeout { get; }

	public abstract CancellationToken CancellationToken { get; }

	protected ServerCallContext(string operationName)
	{
		if (string.IsNullOrWhiteSpace(operationName))
		{
			throw new ArgumentNullException("operationName");
		}
		OperationName = operationName;
	}

	public abstract object[] GetOperationParameters();

	public abstract string GetClientAddress();

	public abstract string GetEndpointAddress();

	public abstract WindowsIdentity GetWindowsIdentity();

	public abstract void Dispose();

	public override string ToString()
	{
		return OperationName;
	}
}
