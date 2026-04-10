import com.sourcegraph.Scip;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

public class ScipJsonExporter {
    private static String q(String value) {
        if (value == null) return "\"\"";
        String escaped = value
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
        return "\"" + escaped + "\"";
    }

    private static String roleBits(int symbolRoles) {
        boolean isDefinition = (symbolRoles & 0x1) != 0;
        boolean isImport = (symbolRoles & 0x2) != 0;
        boolean isWrite = (symbolRoles & 0x4) != 0;
        boolean isRead = (symbolRoles & 0x8) != 0;
        boolean isGenerated = (symbolRoles & 0x10) != 0;
        boolean isTest = (symbolRoles & 0x20) != 0;
        boolean isForwardDef = (symbolRoles & 0x40) != 0;
        return "{"
                + "\"definition\":" + isDefinition + ","
                + "\"import\":" + isImport + ","
                + "\"write\":" + isWrite + ","
                + "\"read\":" + isRead + ","
                + "\"generated\":" + isGenerated + ","
                + "\"test\":" + isTest + ","
                + "\"forward_definition\":" + isForwardDef
                + "}";
    }

    private static String rangeToJson(Scip.Occurrence o) {
        StringBuilder sb = new StringBuilder();
        sb.append("[");
        for (int i = 0; i < o.getRangeCount(); i++) {
            if (i > 0) sb.append(",");
            sb.append(o.getRange(i));
        }
        sb.append("]");
        return sb.toString();
    }

    private static String enclosingRangeToJson(Scip.Occurrence o) {
        StringBuilder sb = new StringBuilder();
        sb.append("[");
        for (int i = 0; i < o.getEnclosingRangeCount(); i++) {
            if (i > 0) sb.append(",");
            sb.append(o.getEnclosingRange(i));
        }
        sb.append("]");
        return sb.toString();
    }

    private static String kindName(Scip.SymbolInformation.Kind kind) {
        return kind == null ? "UnspecifiedKind" : kind.name();
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("usage: ScipJsonExporter <index.scip>");
            System.exit(2);
        }

        Path indexPath = Path.of(args[0]);
        Scip.Index index = Scip.Index.parseFrom(Files.readAllBytes(indexPath));

        Map<String, String> displayBySymbol = new HashMap<>();
        Map<String, String> enclosingBySymbol = new HashMap<>();
        Map<String, String> kindBySymbol = new HashMap<>();

        for (Scip.Document d : index.getDocumentsList()) {
            for (Scip.SymbolInformation s : d.getSymbolsList()) {
                displayBySymbol.put(s.getSymbol(), s.getDisplayName());
                enclosingBySymbol.put(s.getSymbol(), s.getEnclosingSymbol());
                kindBySymbol.put(s.getSymbol(), kindName(s.getKind()));
            }
        }

        for (Scip.SymbolInformation s : index.getExternalSymbolsList()) {
            displayBySymbol.putIfAbsent(s.getSymbol(), s.getDisplayName());
            enclosingBySymbol.putIfAbsent(s.getSymbol(), s.getEnclosingSymbol());
            kindBySymbol.putIfAbsent(s.getSymbol(), kindName(s.getKind()));
        }

        // Metadata line
        String toolName = index.hasMetadata() && index.getMetadata().hasToolInfo()
                ? index.getMetadata().getToolInfo().getName()
                : "";
        String toolVersion = index.hasMetadata() && index.getMetadata().hasToolInfo()
                ? index.getMetadata().getToolInfo().getVersion()
                : "";
        String projectRoot = index.hasMetadata() ? index.getMetadata().getProjectRoot() : "";

        System.out.println("{"
                + "\"type\":\"meta\"," 
                + "\"project_root\":" + q(projectRoot) + ","
                + "\"tool_name\":" + q(toolName) + ","
                + "\"tool_version\":" + q(toolVersion) + ","
                + "\"documents_count\":" + index.getDocumentsCount() + ","
                + "\"external_symbols_count\":" + index.getExternalSymbolsCount()
                + "}");

        for (Scip.Document d : index.getDocumentsList()) {
            String docPath = d.getRelativePath();

            System.out.println("{"
                    + "\"type\":\"document\"," 
                    + "\"path\":" + q(docPath) + ","
                    + "\"language\":" + q(d.getLanguage()) + ","
                    + "\"symbols_count\":" + d.getSymbolsCount() + ","
                    + "\"occurrences_count\":" + d.getOccurrencesCount()
                    + "}");

            for (Scip.SymbolInformation s : d.getSymbolsList()) {
                String symbol = s.getSymbol();
                String display = s.getDisplayName();
                String enclosing = s.getEnclosingSymbol();
                String kind = kindName(s.getKind());

                System.out.println("{"
                        + "\"type\":\"symbol\"," 
                        + "\"symbol\":" + q(symbol) + ","
                        + "\"display_name\":" + q(display) + ","
                        + "\"enclosing_symbol\":" + q(enclosing) + ","
                        + "\"kind\":" + q(kind) + ","
                        + "\"document\":" + q(docPath)
                        + "}");
            }

            for (Scip.Occurrence o : d.getOccurrencesList()) {
                String symbol = o.getSymbol();
                String display = displayBySymbol.getOrDefault(symbol, "");
                String enclosing = enclosingBySymbol.getOrDefault(symbol, "");
                String kind = kindBySymbol.getOrDefault(symbol, "");
                int roles = o.getSymbolRoles();

                System.out.println("{"
                        + "\"type\":\"occurrence\"," 
                        + "\"symbol\":" + q(symbol) + ","
                        + "\"display_name\":" + q(display) + ","
                        + "\"enclosing_symbol\":" + q(enclosing) + ","
                        + "\"kind\":" + q(kind) + ","
                        + "\"document\":" + q(docPath) + ","
                        + "\"range\":" + rangeToJson(o) + ","
                        + "\"enclosing_range\":" + enclosingRangeToJson(o) + ","
                        + "\"symbol_roles\":" + roles + ","
                        + "\"roles\":" + roleBits(roles)
                        + "}");
            }
        }
    }
}
