using System.Globalization;
using System.Text.Json;
using LibreHardwareMonitor.Hardware;

var modulesDirectory = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
var output = new Dictionary<string, object?>
{
    ["cpu"] = new Dictionary<string, object?>
    {
        ["name"] = "Sensor não suportado pelo hardware.",
        ["manufacturer"] = "Sensor não suportado pelo hardware.",
        ["clock_current"] = "Sensor não suportado pelo hardware.",
        ["clock_max"] = "Sensor não suportado pelo hardware.",
        ["usage"] = "Sensor não suportado pelo hardware.",
        ["usage_per_core"] = new List<string>(),
        ["physical_cores"] = "Sensor não suportado pelo hardware.",
        ["threads"] = "Sensor não suportado pelo hardware.",
        ["temperature"] = "Sensor não suportado pelo hardware."
    },
    ["memory"] = new Dictionary<string, object?>
    {
        ["total"] = "Sensor não suportado pelo hardware.",
        ["used"] = "Sensor não suportado pelo hardware.",
        ["free"] = "Sensor não suportado pelo hardware.",
        ["percent"] = "Sensor não suportado pelo hardware.",
        ["speed"] = "Sensor não suportado pelo hardware.",
        ["type"] = "Sensor não suportado pelo hardware."
    },
    ["disks"] = new List<Dictionary<string, object?>>(),
    ["gpu"] = new Dictionary<string, object?>(),
    ["motherboard"] = new Dictionary<string, object?>(),
    ["system"] = new Dictionary<string, object?>
    {
        ["computer_name"] = Environment.MachineName,
        ["os_name"] = Environment.OSVersion.VersionString,
        ["version"] = Environment.OSVersion.VersionString,
        ["build"] = Environment.OSVersion.VersionString,
        ["architecture"] = Environment.Is64BitOperatingSystem ? "x64" : "x86"
    },
    ["sensors"] = new List<Dictionary<string, object?>>(),
    ["debug_file"] = string.Empty,
    ["dll_path"] = modulesDirectory,
    ["search_paths"] = new List<string> { modulesDirectory },
    ["collected_at"] = DateTime.Now.ToString("dd/MM/yyyy HH:mm:ss")
};

var computer = new Computer
{
    IsCpuEnabled = true,
    IsMemoryEnabled = true,
    IsMotherboardEnabled = false,
    IsStorageEnabled = true,
    IsControllerEnabled = false,
    IsGpuEnabled = true
};

computer.Open();

var sensors = (List<Dictionary<string, object?>>)output["sensors"]!;
var disks = (List<Dictionary<string, object?>>)output["disks"]!;
var cpu = (Dictionary<string, object?>)output["cpu"]!;
var memory = (Dictionary<string, object?>)output["memory"]!;

foreach (var hardware in computer.Hardware)
{
    var typeName = hardware.HardwareType.ToString().ToLowerInvariant();
    if (typeName == "cpu")
    {
        cpu["name"] = hardware.Name;
    }

    foreach (ISensor sensor in hardware.Sensors)
    {
        if (sensor.Value is null)
        {
            continue;
        }

        sensors.Add(new Dictionary<string, object?>
        {
            ["hardware"] = hardware.Name,
            ["hardware_type"] = hardware.HardwareType.ToString(),
            ["sensor"] = sensor.Name,
            ["sensor_type"] = sensor.SensorType.ToString(),
            ["value"] = FormatSensorValue(sensor)
        });

        if (typeName == "cpu")
        {
            if (sensor.SensorType == SensorType.Load)
            {
                if (sensor.Name.Contains("total", StringComparison.OrdinalIgnoreCase) || sensor.Name.Contains("package", StringComparison.OrdinalIgnoreCase) || sensor.Name.Contains("cpu", StringComparison.OrdinalIgnoreCase))
                {
                    cpu["usage"] = $"{Convert.ToDouble(sensor.Value).ToString("F1", CultureInfo.InvariantCulture)}%";
                }
                else
                {
                    var usagePerCore = (List<string>)cpu["usage_per_core"]!;
                    usagePerCore.Add($"{sensor.Name}: {Convert.ToDouble(sensor.Value).ToString("F1", CultureInfo.InvariantCulture)}%");
                }
            }
            else if (sensor.SensorType == SensorType.Clock)
            {
                var clockCurrent = (string?)cpu["clock_current"];
                if (clockCurrent == "Sensor não suportado pelo hardware." && (sensor.Name.Contains("current", StringComparison.OrdinalIgnoreCase) || sensor.Name.Contains("base", StringComparison.OrdinalIgnoreCase)))
                {
                    cpu["clock_current"] = $"{Convert.ToDouble(sensor.Value).ToString("F0", CultureInfo.InvariantCulture)} MHz";
                }

                var clockMax = (string?)cpu["clock_max"];
                if (clockMax == "Sensor não suportado pelo hardware." && (sensor.Name.Contains("max", StringComparison.OrdinalIgnoreCase) || sensor.Name.Contains("boost", StringComparison.OrdinalIgnoreCase)))
                {
                    cpu["clock_max"] = $"{Convert.ToDouble(sensor.Value).ToString("F0", CultureInfo.InvariantCulture)} MHz";
                }
            }
            else if (sensor.SensorType == SensorType.Temperature)
            {
                var temp = Convert.ToDouble(sensor.Value);
                var currentTemp = (string?)cpu["temperature"];
                if (currentTemp == "Sensor não suportado pelo hardware." || temp > Convert.ToDouble(currentTemp.Replace("°C", "")))
                {
                    cpu["temperature"] = $"{temp.ToString("F1", CultureInfo.InvariantCulture)}°C";
                }
            }
        }
        else if (typeName == "memory")
        {
            if (sensor.SensorType == SensorType.Data)
            {
                var label = sensor.Name.ToLowerInvariant();
                var valueBytes = Convert.ToDouble(sensor.Value);
                var valueGb = valueBytes / (1024.0 * 1024.0 * 1024.0);

                if (label.Contains("used"))
                {
                    memory["used"] = $"{valueGb.ToString("F2", CultureInfo.InvariantCulture)} GB";
                }
                else if (label.Contains("available") || label.Contains("free"))
                {
                    memory["free"] = $"{valueGb.ToString("F2", CultureInfo.InvariantCulture)} GB";
                }
                else if (label.Contains("size") || label.Contains("capacity") || label.Contains("total"))
                {
                    memory["total"] = $"{valueGb.ToString("F2", CultureInfo.InvariantCulture)} GB";
                }
            }
        }
        else if (typeName.Contains("storage") || typeName.Contains("disk") || typeName.Contains("ssd") || typeName.Contains("hdd"))
        {
            var diskRecord = disks.FirstOrDefault(item => string.Equals((string?)item["name"], hardware.Name, StringComparison.OrdinalIgnoreCase));
            if (diskRecord is null)
            {
                diskRecord = new Dictionary<string, object?>
                {
                    ["name"] = hardware.Name,
                    ["model"] = hardware.Name,
                    ["type"] = typeName,
                    ["total"] = "Sensor não suportado pelo hardware.",
                    ["used"] = "Sensor não suportado pelo hardware.",
                    ["free"] = "Sensor não suportado pelo hardware.",
                    ["temperature"] = "Sensor não suportado pelo hardware.",
                    ["smart_health"] = "Sensor não suportado pelo hardware.",
                    ["remaining_life"] = "Sensor não suportado pelo hardware.",
                    ["power_on_hours"] = "Sensor não suportado pelo hardware."
                };
                disks.Add(diskRecord);
            }

            if (sensor.SensorType == SensorType.Temperature)
            {
                diskRecord["temperature"] = $"{Convert.ToDouble(sensor.Value).ToString("F1", CultureInfo.InvariantCulture)}°C";
            }
            else if (sensor.SensorType == SensorType.Level)
            {
                var label = sensor.Name.ToLowerInvariant();
                if (label.Contains("remaining life") || label.Contains("life"))
                {
                    diskRecord["remaining_life"] = $"{Convert.ToDouble(sensor.Value).ToString("F1", CultureInfo.InvariantCulture)}%";
                }
                else if (label.Contains("health") || label.Contains("overall health"))
                {
                    diskRecord["smart_health"] = $"{Convert.ToDouble(sensor.Value).ToString("F1", CultureInfo.InvariantCulture)}%";
                }
                else if (label.Contains("power on") || label.Contains("hours"))
                {
                    diskRecord["power_on_hours"] = $"{Convert.ToDouble(sensor.Value).ToString("F0", CultureInfo.InvariantCulture)}";
                }
            }
        }
    }
}

var json = JsonSerializer.Serialize(output, new JsonSerializerOptions { WriteIndented = false });
Console.WriteLine(json);

static string FormatSensorValue(ISensor sensor)
{
    if (sensor.Value is null)
    {
        return "Sensor não suportado pelo hardware.";
    }

    return sensor.SensorType switch
    {
        SensorType.Temperature => $"{Convert.ToDouble(sensor.Value).ToString("F1", CultureInfo.InvariantCulture)}°C",
        SensorType.Load => $"{Convert.ToDouble(sensor.Value).ToString("F1", CultureInfo.InvariantCulture)}%",
        SensorType.Power => $"{Convert.ToDouble(sensor.Value).ToString("F1", CultureInfo.InvariantCulture)} W",
        _ => $"{Convert.ToDouble(sensor.Value).ToString("F1", CultureInfo.InvariantCulture)}"
    };
}
