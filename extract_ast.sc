import java.nio.file.{Files, Paths, Path}
import java.io.File

// Root directory for saving AST dot files
val astRoot = "/Users/omnisceo/Desktop/spring_2025/Binary_Program_VC/ast_files"

// Helper function to sanitize file names
def cleanFileName(name: String): String = {
  name.replaceAll("[^a-zA-Z0-9]", "_")
}

// For each method in each file
cpg.file.name.l.foreach { filename =>
  val methods = cpg.method.fileExact(filename).nameNot("<global>").l
  val fileHash = cleanFileName(filename)

  // Find a matching CFG folder name that this file belongs to
  val labelFolderOpt = os.list(os.Path("/Users/omnisceo/Desktop/spring_2025/Binary_Program_VC/pt_cfg_files"))
    .map(_.last)
    .find(_.contains(fileHash.takeRight(9)))  // Match based on file hash suffix (adjust if needed)

  labelFolderOpt match {
    case Some(labelFolder) =>
      val outDir = Paths.get(astRoot, labelFolder)
      if (!Files.exists(outDir)) Files.createDirectories(outDir)

      methods.zipWithIndex.foreach { case (m, idx) =>
        val dotGraph = m.ast.dot
        val fileName = s"$idx-ast.dot"
        val filePath = outDir.resolve(fileName)
        Files.write(filePath, dotGraph.getBytes)
      }

    case None =>
      println(s"⚠️  No matching label folder found for file: $filename")
  }
}
