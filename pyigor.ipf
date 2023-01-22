#pragma TextEncoding = "UTF-8"
#pragma rtGlobals=3		// Use modern global access method and strict wave access.

Function/S PyIgorSendMessage(port, msg)
	String msg
	Variable port
	String baseURL = "http://127.0.0.1:"+num2istr(port)+"/msg/"
	
	String response = FetchURL(baseURL + msg)
	Variable error = GetRTError(1)
   if (error)
      return "error:cannot_connect"
   endif
	return response
End

Function/S PyIgorCall(commands)
	String commands
	String results
	Variable port = 15556
	String baseURL = "http://127.0.0.1:"+num2istr(port)+"/call/"
	String response = FetchURL(baseURL + commands)
	Variable error = GetRTError(1)
   if (error)
      print "Cannot call PyIgor"
   endif
	return response
End

Function PyIgorOutputWave(port, uid, wvName, filePath)
	Variable port
	String uid
	String wvName, filePath
	Variable fileID
	
	if (!exists(wvName))
		Print "Wave "+wvName+" not found."
		if (strlen(uid) > 0)
			PyIgorSendMessage(port, "error/"+uid)
		endif
		return -1
	endif
	HDF5CreateFile/O/Z fileID as PyIgorConvertPathStr(filePath)
	if (V_flag != 0)
		Print "HDF5CreateFile failed"
		if (strlen(uid) > 0)
			PyIgorSendMessage(port, "error/"+uid)
		endif
		return -1
	endif
	HDF5SaveData/O/Z $wvName, fileID, uid
	if (V_flag != 0)
		Print "HDF5SaveData failed"
		if (strlen(uid) > 0)
			PyIgorSendMessage(port, "error/"+uid)
		endif
		HDF5CloseFile fileID
		return -1
	endif
	HDF5CloseFile fileID
	if (strlen(uid) > 0)
		PyIgorSendMessage(port, "get/"+uid)
	endif
End

Function PyIgorLoadWave(port, uid, wvName, filePath, flag)
	Variable port
	String uid
	String wvName, filePath
	Variable flag
	Variable fileID
	
	if (strlen(wvName) == 0)
		wvName = UniqueName("wave", 1, 0)
	endif
	
	HDF5OpenFile/R fileID as PyIgorConvertPathStr(filePath)
	if (V_flag != 0)
		Print "HDF5OpenFile failed"
		if (strlen(uid) > 0)
			PyIgorSendMessage(port, "error/"+uid)
		endif
		return -1
	endif
	HDF5LoadData/O/Q/Z/N=$wvName fileID, uid
	if (V_flag != 0)
		Print "HDF5LoadData failed"
		if (strlen(uid) > 0)
			PyIgorSendMessage(port, "error/"+uid)
		endif
		return -1
	endif
	HDF5CloseFile fileID
	if (strlen(uid) > 0)
		PyIgorSendMessage(port, "put/"+uid)
	endif
End

Function/S PyIgorConvertPathStr(pathStr)
	String pathStr
	if (StringMatch(pathStr, ":*"))
		return ParseFilePath(0, SpecialDirPath("Igor Executable", 0, 0, 0), ":", 0, 0) + pathStr
	endif
	return pathStr
End