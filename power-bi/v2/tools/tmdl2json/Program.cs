// tmdl2json <tmdl folder> <DataModelSchema output>
// Parses a TMDL model folder with Microsoft's Tabular Object Model (fails on any TMDL error),
// fills the Power BI Desktop model settings, and writes the model as TMSL JSON in UTF-16 LE,
// which is the format of the DataModelSchema entry inside a .pbit template.
using System.Text;
using Microsoft.AnalysisServices.Tabular;

var db = TmdlSerializer.DeserializeDatabaseFromFolder(args[0]);
var model = db.Model;
model.DataAccessOptions = new DataAccessOptions { LegacyRedirects = true, ReturnErrorValuesAsNull = true };
model.DefaultPowerBIDataSourceVersion = PowerBIDataSourceVersion.PowerBI_V3;
model.SourceQueryCulture = model.Culture;

string Tag() => Guid.NewGuid().ToString();
foreach (var e in model.Expressions) if (string.IsNullOrEmpty(e.LineageTag)) e.LineageTag = Tag();
foreach (var t in model.Tables)
{
    if (string.IsNullOrEmpty(t.LineageTag)) t.LineageTag = Tag();
    foreach (var c in t.Columns) if (c.Type != ColumnType.RowNumber && string.IsNullOrEmpty(c.LineageTag)) c.LineageTag = Tag();
    foreach (var m in t.Measures) if (string.IsNullOrEmpty(m.LineageTag)) m.LineageTag = Tag();
}

var json = JsonSerializer.SerializeDatabase(db, new SerializeOptions
{
    IgnoreTimestamps = true, IgnoreInferredObjects = true, IgnoreInferredProperties = true, SplitMultilineStrings = true
});
File.WriteAllText(args[1], json, new UnicodeEncoding(false, false));

// summary + a round trip through the JSON deserializer as a second check
var back = JsonSerializer.DeserializeDatabase(json);
Console.WriteLine($"OK  compatibilityLevel={back.CompatibilityLevel}  expressions={back.Model.Expressions.Count}");
foreach (var t in back.Model.Tables)
    Console.WriteLine($"    table '{t.Name}': {t.Columns.Count(c => c.Type == ColumnType.Data)} columns, {t.Measures.Count} measures, partition={t.Partitions[0].SourceType}");
