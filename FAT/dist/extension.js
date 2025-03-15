/******/ (() => { // webpackBootstrap
/******/ 	"use strict";
/******/ 	var __webpack_modules__ = ([
/* 0 */
/***/ (function(__unused_webpack_module, exports, __webpack_require__) {


var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", ({ value: true }));
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(__webpack_require__(1));
const child_process_1 = __webpack_require__(2);
const path = __importStar(__webpack_require__(3));
function activate(context) {
    console.log('Firmware Analysis Tool "FAT" is now active (auto-start).');
    // 1) Immediately run analysis when the extension activates.
    runAnalysisAndShowCFG();
}
async function runAnalysisAndShowCFG() {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
        vscode.window.showErrorMessage('No workspace folder open.');
        return;
    }
    const workspacePath = workspaceFolders[0].uri.fsPath;
    // Paths to your Python scripts and files
    const scriptPath = path.join(workspacePath, 'rda_disassembler_enhanced.py');
    const generateReportPath = path.join(workspacePath, 'generate_report.py');
    const firmwarePath = path.join(workspacePath, 'firmware', 'latest_firmware.bin');
    const logPath = path.join(workspacePath, 'firmware', 'disassembly.log');
    const reportPath = path.join(workspacePath, 'firmware', 'report.md');
    const cfgDotPath = path.join(workspacePath, 'firmware', 'cfg.dot');
    const cfgPngPath = path.join(workspacePath, 'firmware', 'cfg.png');
    // 2) Run the firmware analysis
    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: "Analyzing Firmware (auto-run)...",
        cancellable: false
    }, async () => {
        // (A) Disassembler
        await runCommand(`python3 "${scriptPath}" "${firmwarePath}"`, workspacePath);
        // (B) Possibly convert cfg.dot to cfg.png:
        //     dot -Tpng cfg.dot -o cfg.png
        // Only do this if you generate .dot automatically.
        // Adjust path if 'dot' is not in your PATH or you need a full path.
        await runCommand(`dot -Tpng "${cfgDotPath}" -o "${cfgPngPath}"`, workspacePath);
        // (C) Generate report
        await runCommand(`python3 "${generateReportPath}" "${logPath}" "${reportPath}"`, workspacePath);
        vscode.window.showInformationMessage('Firmware analysis completed successfully (auto-run)!');
        // 3) Show the CFG image in a webview
        showCFGWebview(cfgPngPath);
    });
}
/**
 * Spawns a shell command & returns a Promise that resolves/fails on completion.
 */
function runCommand(command, cwd) {
    return new Promise((resolve, reject) => {
        (0, child_process_1.exec)(command, { cwd }, (error, stdout, stderr) => {
            if (error) {
                vscode.window.showErrorMessage(`Command failed: ${error.message}`);
                reject(error);
            }
            else {
                resolve();
            }
        });
    });
}
/**
 * Opens a new webview panel and displays the CFG image.
 */
function showCFGWebview(cfgPath) {
    const panel = vscode.window.createWebviewPanel('firmwareCFG', // internal identifier
    'Firmware Control Flow Graph', // title in the tab
    vscode.ViewColumn.One, // show in the first editor column
    {
        enableScripts: true // if you need JS in the webview
    });
    // Convert local file path to a webview URI
    const cfgUri = panel.webview.asWebviewUri(vscode.Uri.file(cfgPath));
    // Basic HTML that displays the PNG
    panel.webview.html = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Firmware CFG</title>
        </head>
        <body>
            <h2>Control Flow Graph</h2>
            <p>CFG generated automatically during analysis.</p>
            <img src="${cfgUri}" />
        </body>
        </html>
    `;
}
function deactivate() {
    console.log('Firmware Analysis Tool "FAT" deactivated.');
}


/***/ }),
/* 1 */
/***/ ((module) => {

module.exports = require("vscode");

/***/ }),
/* 2 */
/***/ ((module) => {

module.exports = require("child_process");

/***/ }),
/* 3 */
/***/ ((module) => {

module.exports = require("path");

/***/ })
/******/ 	]);
/************************************************************************/
/******/ 	// The module cache
/******/ 	var __webpack_module_cache__ = {};
/******/ 	
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/ 		// Check if module is in cache
/******/ 		var cachedModule = __webpack_module_cache__[moduleId];
/******/ 		if (cachedModule !== undefined) {
/******/ 			return cachedModule.exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = __webpack_module_cache__[moduleId] = {
/******/ 			// no module.id needed
/******/ 			// no module.loaded needed
/******/ 			exports: {}
/******/ 		};
/******/ 	
/******/ 		// Execute the module function
/******/ 		__webpack_modules__[moduleId].call(module.exports, module, module.exports, __webpack_require__);
/******/ 	
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/ 	
/************************************************************************/
/******/ 	
/******/ 	// startup
/******/ 	// Load entry module and return exports
/******/ 	// This entry module is referenced by other modules so it can't be inlined
/******/ 	var __webpack_exports__ = __webpack_require__(0);
/******/ 	module.exports = __webpack_exports__;
/******/ 	
/******/ })()
;
//# sourceMappingURL=extension.js.map