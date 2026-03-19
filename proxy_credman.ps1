Set-StrictMode -Version Latest

if (-not ("CredMan.Native" -as [type])) {
  Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

namespace CredMan {
  public enum CredType : int {
    Generic = 1
  }

  [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
  public struct NativeCredential {
    public UInt32 Flags;
    public UInt32 Type;
    public string TargetName;
    public string Comment;
    public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
    public UInt32 CredentialBlobSize;
    public IntPtr CredentialBlob;
    public UInt32 Persist;
    public UInt32 AttributeCount;
    public IntPtr Attributes;
    public string TargetAlias;
    public string UserName;
  }

  public class Native {
    [DllImport("Advapi32.dll", CharSet = CharSet.Unicode, EntryPoint = "CredReadW", SetLastError = true)]
    public static extern bool CredRead(string target, int type, int reservedFlag, out IntPtr credentialPtr);

    [DllImport("Advapi32.dll", SetLastError = true)]
    public static extern void CredFree([In] IntPtr cred);
  }
}
"@
}

function Get-CredManGenericCredential {
  param(
    [Parameter(Mandatory = $true)][string]$TargetName
  )

  $credPtr = [IntPtr]::Zero
  $ok = [CredMan.Native]::CredRead($TargetName, [int][CredMan.CredType]::Generic, 0, [ref]$credPtr)
  if (-not $ok) {
    return $null
  }

  try {
    $native = [Runtime.InteropServices.Marshal]::PtrToStructure($credPtr, [type][CredMan.NativeCredential])
    $password = ""
    if ($native.CredentialBlob -ne [IntPtr]::Zero -and $native.CredentialBlobSize -gt 0) {
      $password = [Runtime.InteropServices.Marshal]::PtrToStringUni($native.CredentialBlob, [int]($native.CredentialBlobSize / 2))
    }
    [pscustomobject]@{
      TargetName = $native.TargetName
      UserName   = $native.UserName
      Password   = $password
    }
  }
  finally {
    if ($credPtr -ne [IntPtr]::Zero) {
      [CredMan.Native]::CredFree($credPtr)
    }
  }
}
