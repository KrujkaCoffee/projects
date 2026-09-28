// TFlex.DOCs.RPC, Version=17.4.2.0, Culture=neutral, PublicKeyToken=null
// TFlex.DOCs.RPC.Services.ServiceServer
using System;
using TFlex.DOCs.Common.Errors;
using TFlex.DOCs.Common.Helpers;
using TFlex.DOCs.RPC.Exceptions;

public abstract class ServiceServer
{
	public virtual ServiceDetailException OnError(Exception exception, string methodName)
	{
		RethrowErrorData error = new RethrowErrorData(ExceptionHelper.ExceptionToString(exception));
		return new ServiceDetailException(methodName, error);
	}

	public virtual void LogError(Exception exception)
	{
	}
}
