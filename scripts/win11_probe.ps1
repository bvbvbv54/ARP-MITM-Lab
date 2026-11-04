<#
.SYNOPSIS
    Victim-side measurement for the ARP lab. Run on the Windows 11 box.

.DESCRIPTION
    Read-only probes for the poisoned-link demo. Nothing here changes
    configuration or writes the ARP cache; it observes what the poisoning
    did from the victim's point of view.

.PARAMETER Mode
    arp       ARP cache dump + gateway MAC flip watch        (default)
    baseline  ARP cache dump + latency/throughput reference
    during    ARP dump + latency + adapter counters (poisoned run)
    counters  adapter byte/packet deltas + established sessions

.PARAMETER GatewayIP
    Gateway IP to probe. Alias: -Gateway.

.PARAMETER Samples
    Number of probes per measurement (default 20).

.PARAMETER WatchSeconds
    Duration of the MAC-flip watch in the arp mode (default 30).

.EXAMPLE
    .\win11_probe.ps1 -Mode arp

.EXAMPLE
    .\win11_probe.ps1 -Mode baseline -GatewayIP 10.0.2.1 -Samples 30

.NOTES
    Require Administrator. PowerShell 5.1+.
#>

[CmdletBinding()]
param(
    [ValidateSet('arp', 'baseline', 'during', 'counters')]
    [string]$Mode = 'arp',

    [Alias('Gateway')]
    [string]$GatewayIP = '10.0.2.1',

    [ValidateRange(1, 500)]
    [int]$Samples = 20,

    [ValidateRange(2, 600)]
    [int]$WatchSeconds = 30
)

$ErrorActionPreference = 'Stop'
$script:DistinctMacs = New-Object System.Collections.Generic.HashSet[string]

function Write-Section {
    param([string]$Text)
    Write-Host "`n=== $Text ===" -ForegroundColor Cyan
}

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator
    )
}

function Get-ActiveAdapter {
    # Prefer the adapter carrying the default route; fall back to first Up.
    $route = Get-NetRoute -DestinationPrefix '0.0.0.0/0' `
        -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($route) {
        $adapter = Get-NetAdapter -InterfaceIndex $route.InterfaceIndex `
            -ErrorAction SilentlyContinue
        if ($adapter) { return $adapter }
    }
    return Get-NetAdapter | Where-Object Status -eq 'Up' |
        Select-Object -First 1
}

function Show-ArpCache {
    Write-Section 'arp -a (raw cache)'
    arp -a

    Write-Section 'Get-NetNeighbor (structured)'
    Get-NetNeighbor -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.State -ne 'Unreachable' } |
        Select-Object IPAddress, LinkLayerAddress, State, InterfaceAlias |
        Format-Table -AutoSize
}

function Get-GatewayMac {
    $entries = Get-NetNeighbor -IPAddress $GatewayIP -ErrorAction SilentlyContinue |
        Where-Object LinkLayerAddress |
        Select-Object -ExpandProperty LinkLayerAddress -Unique
    return ($entries -join ', ')
}

function Watch-GatewayMac {
    $rounds = [Math]::Max([int]($WatchSeconds / 2), 1)
    Write-Section "gateway MAC watch (2s poll, $rounds rounds)"

    for ($i = 0; $i -lt $rounds; $i++) {
        $mac = Get-GatewayMac
        $stamp = Get-Date -Format 'HH:mm:ss'

        if ([string]::IsNullOrWhiteSpace($mac)) {
            Write-Host "[$stamp] <no neighbor entry>" -ForegroundColor DarkGray
        } elseif ($script:DistinctMacs.Add($mac)) {
            Write-Host "[$stamp] NEW gateway MAC: $mac" -ForegroundColor Yellow
        } else {
            Write-Host "[$stamp] $mac"
        }
        Start-Sleep -Seconds 2
    }

    $seen = @($script:DistinctMacs)
    Write-Host "`nDistinct gateway MACs observed: $($seen -join ', ')"
    if ($seen.Count -gt 1) {
        Write-Host 'More than one MAC for one IP in a short window = cache poisoning.' `
            -ForegroundColor Yellow
    } else {
        Write-Host 'Single stable MAC observed.' -ForegroundColor Green
    }
}

function Measure-Ping {
    Write-Section "ICMP latency vs $GatewayIP ($Samples pings)"
    $replies = @(Test-Connection -ComputerName $GatewayIP -Count $Samples `
        -ErrorAction SilentlyContinue)

    if ($replies.Count -gt 0) {
        $times = @($replies | ForEach-Object { $_.ResponseTime })
        $stats = $times | Measure-Object -Average -Maximum -Minimum
        $loss = (($Samples - $times.Count) / $Samples) * 100
        Write-Host ('min={0}ms avg={1:N1}ms max={2}ms loss={3:N0}%' -f `
            $stats.Minimum, $stats.Average, $stats.Maximum, $loss)
    } else {
        Write-Host 'no replies — gateway unreachable (poison in effect?)' `
            -ForegroundColor Red
    }
}

function Measure-TcpHandshake {
    Write-Section "TCP handshake RTT to ${GatewayIP}:443"
    $rtts = New-Object System.Collections.Generic.List[double]

    for ($i = 0; $i -lt $Samples; $i++) {
        $watch = [System.Diagnostics.Stopwatch]::StartNew()
        $client = New-Object System.Net.Sockets.TcpClient
        try {
            $task = $client.ConnectAsync($GatewayIP, 443)
            if ($task.Wait(1500)) {
                $rtts.Add($watch.Elapsed.TotalMilliseconds)
            }
        } catch {
            # refused/timed out: leave it out of the sample
        } finally {
            $client.Close()
            $watch.Stop()
        }
    }

    if ($rtts.Count -gt 0) {
        $avg = ($rtts | Measure-Object -Average).Average
        Write-Host ('tcp rtt avg={0:N1}ms over {1}/{2} connects' -f `
            $avg, $rtts.Count, $Samples)
    } else {
        Write-Host 'all TCP connects failed/timed out' -ForegroundColor Red
    }
}

function Show-Counters {
    $adapter = Get-ActiveAdapter
    if (-not $adapter) {
        Write-Host 'no active adapter found' -ForegroundColor Red
        return
    }

    Write-Section "adapter counters on $($adapter.Name) (2s sample)"
    $before = Get-NetAdapterStatistics -Name $adapter.Name
    Start-Sleep -Seconds 2
    $after = Get-NetAdapterStatistics -Name $adapter.Name

    [pscustomobject]@{
        'RxPackets'      = $after.ReceivedUnicastPackets - $before.ReceivedUnicastPackets
        'TxPackets'      = $after.SentUnicastPackets - $before.SentUnicastPackets
        'RxBytes'        = $after.ReceivedBytes - $before.ReceivedBytes
        'TxBytes'        = $after.SentBytes - $before.SentBytes
        'RxDiscards'     = $after.ReceivedDiscardedPackets - $before.ReceivedDiscardedPackets
        'OutboundErrors' = $after.OutboundPacketsWithNoProtocol -
                           $before.OutboundPacketsWithNoProtocol
    } | Format-List

    Write-Section 'established sessions (who do I actually talk to)'
    Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue |
        Group-Object RemoteAddress |
        Sort-Object Count -Descending |
        Select-Object -First 10 Count, Name |
        Format-Table -AutoSize
}

function Show-Summary {
    $adapter = Get-ActiveAdapter
    Write-Section 'summary'
    [pscustomobject]@{
        Time        = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
        Mode        = $Mode
        Gateway     = $GatewayIP
        GatewayMac  = (Get-GatewayMac)
        DistinctMac = (@($script:DistinctMacs) -join ', ')
        Adapter     = if ($adapter) { $adapter.Name } else { '<none>' }
        Admin       = (Test-Admin)
    } | Format-List
}

if (-not (Test-Admin)) {
    Write-Host 'not running as Administrator — neighbor/counter data may be limited' `
        -ForegroundColor Yellow
}

switch ($Mode) {
    'arp'      { Show-ArpCache; Watch-GatewayMac }
    'baseline' { Show-ArpCache; Measure-Ping; Measure-TcpHandshake }
    'during'   { Show-ArpCache; Measure-Ping; Measure-TcpHandshake; Show-Counters }
    'counters' { Show-Counters }
}

Show-Summary
