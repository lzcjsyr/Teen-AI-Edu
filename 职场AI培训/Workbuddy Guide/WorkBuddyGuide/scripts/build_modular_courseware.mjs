import { execFile } from "node:child_process";
import {
  chmod,
  cp,
  mkdir,
  readdir,
  readFile,
  rm,
  stat,
  symlink,
  writeFile,
} from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(scriptDirectory, "..");
const bluebookRoot = path.join(projectRoot, "docs", "bluebook");
const stagingRoot = path.join(projectRoot, ".modular-courseware-build");
const outputRoot = path.resolve(projectRoot, "..", "WorkBuddyGuide_散装版");
const vitepressBin = path.join(projectRoot, "node_modules", ".bin", "vitepress");

const parts = {
  first: "第一篇 使用手册：先把 WorkBuddy 用起来",
  second: "第二篇 案例篇：从一项任务到一支 AI 团队",
  third: "第三篇 进阶篇：把案例变成自己的工作系统",
  fourth: "第四篇 岗位与行业落地",
};

const chapterNumber = (name) => {
  const match = name.match(/^第\s*(\d+)\s*章/);
  return match ? Number(match[1]) : Number.POSITIVE_INFINITY;
};

const chapterTitle = (name) => name.replace(/^第\s*\d+\s*章\s*/, "").trim();

const chapterRoute = (name) => {
  const number = chapterNumber(name);
  return Number.isFinite(number) ? `chapter-${String(number).padStart(2, "0")}` : "extra-reading";
};

const listChapterDirectories = async (partName) => {
  const entries = await readdir(path.join(bluebookRoot, partName), {
    withFileTypes: true,
  });

  return entries
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort((left, right) => {
      const difference = chapterNumber(left) - chapterNumber(right);
      if (Number.isFinite(difference) && difference !== 0) return difference;
      if (Number.isFinite(chapterNumber(left))) return -1;
      if (Number.isFinite(chapterNumber(right))) return 1;
      return left.localeCompare(right, "zh-CN");
    });
};

const firstChapters = await listChapterDirectories(parts.first);
const secondChapters = await listChapterDirectories(parts.second);
const thirdChapters = await listChapterDirectories(parts.third);
const fourthChapters = await listChapterDirectories(parts.fourth);

const modules = [
  {
    folder: "01_第一篇使用手册",
    route: "01_manual",
    title: parts.first,
    source: path.join(bluebookRoot, parts.first),
    chapters: firstChapters,
    kind: "collection",
  },
  ...secondChapters.map((chapter) => ({
    folder: {
      11: "11_办公三件套",
      12: "12_整理桌面文件",
      13: "13_远程控制电脑",
      14: "14_生活助手",
      15: "15_资讯整合每日通知",
      16: "16_知识管理",
      17: "17_会议后续工作",
      18: "18_投资分析",
      19: "19_人工智能视频团队",
      20: "20_自媒体增长闭环",
      21: "21_生成式引擎优化",
    }[chapterNumber(chapter)],
    route: {
      11: "11_case_office-suite",
      12: "12_case_file-organizing",
      13: "13_case_remote-control",
      14: "14_case_life-assistant",
      15: "15_case_information-feed",
      16: "16_case_knowledge-management",
      17: "17_case_meeting-followup",
      18: "18_case_investment-analysis",
      19: "19_case_ai-video-team",
      20: "20_case_creator-growth",
      21: "21_case_geo",
    }[chapterNumber(chapter)],
    title: chapter,
    source: path.join(bluebookRoot, parts.second, chapter),
    chapters: [],
    kind: "case",
  })),
  ...thirdChapters.map((chapter) => ({
    folder: {
      22: "22_打造技能",
      23: "23_实操案例集",
      24: "24_多智能体系统设计",
      25: "25_自动化工作流可靠性",
    }[chapterNumber(chapter)],
    route: {
      22: "22_advanced_skill-building",
      23: "23_advanced_examples",
      24: "24_advanced_multi-agent",
      25: "25_advanced_reliable-automation",
    }[chapterNumber(chapter)],
    title: chapter,
    source: path.join(bluebookRoot, parts.third, chapter),
    chapters: [],
    kind: "case",
  })),
  {
    folder: "26_第四篇岗位与行业落地",
    route: "26_industry-roadmaps",
    title: parts.fourth,
    source: path.join(bluebookRoot, parts.fourth),
    chapters: fourthChapters,
    kind: "collection",
  },
];

const json = (value) => JSON.stringify(value, null, 2);

const configSource = (module) => {
  const sidebar =
    module.kind === "collection"
      ? [
          { text: "本篇导读", link: "/" },
          ...module.chapters.map((chapter) => ({
            text: chapter,
            link: `/${chapterRoute(chapter)}/`,
          })),
        ]
      : false;

  return `import { defineConfig } from "vitepress";
import { configureMermaidMarkdown } from "./mermaid-markdown";

export default defineConfig({
  lang: "zh-CN",
  title: ${json(module.title)},
  titleTemplate: false,
  description: ${json(`${module.title} · WorkBuddy 独立课件`)},
  base: ${json(`/.routes/${module.route}/`)},
  cleanUrls: false,
  appearance: false,
  lastUpdated: false,
  srcExclude: ["**/source.md"],
  markdown: {
    config: configureMermaidMarkdown,
    image: { lazyLoading: true },
    theme: { light: "github-light", dark: "github-light" },
  },
  transformPageData(pageData) {
    pageData.frontmatter.navbar = false;
    pageData.frontmatter.editLink = false;
    pageData.frontmatter.lastUpdated = false;
    ${module.kind === "case" ? "pageData.frontmatter.sidebar = false;\n    pageData.frontmatter.prev = false;\n    pageData.frontmatter.next = false;" : ""}
  },
  themeConfig: {
    siteTitle: false,
    nav: [],
    sidebar: ${json(sidebar)},
    socialLinks: [],
    outline: { level: [2, 3], label: "本页目录" },
    docFooter: ${module.kind === "collection" ? '{ prev: "上一章", next: "下一章" }' : "false"},
    lastUpdated: false,
    editLink: false,
  },
});
`;
};

const themeSource = `import { defineAsyncComponent, h } from "vue";
import DefaultTheme from "vitepress/theme-without-fonts";
import ImageLightbox from "./components/ImageLightbox.vue";

import "./style.css";
import "./modular.css";

export default {
  extends: DefaultTheme,
  Layout: () =>
    h(DefaultTheme.Layout, null, {
      "layout-bottom": () => h(ImageLightbox),
    }),
  enhanceApp({ app }) {
    app.component(
      "MermaidDiagram",
      defineAsyncComponent(() => import("./components/MermaidDiagram.vue")),
    );

  },
};
`;

const modularCss = `/* 独立课件：移除原网站级导航，只保留内容与必要的篇内目录。 */
.VPNav,
.VPLocalNav,
.VPFooter,
.VPDocFooter .edit-info,
.VPDocFooter .last-updated,
.VPDocFooter .edit-link-button {
  display: none !important;
}

.Layout {
  padding-top: 0 !important;
}

.VPSidebar {
  top: 0 !important;
  padding-top: 28px !important;
}

.VPContent,
.VPContent.has-sidebar {
  padding-top: 0 !important;
}

.VPDoc {
  padding-top: 38px !important;
}

.VPDoc.has-aside .content-container,
.VPDoc:not(.has-sidebar) .content-container {
  max-width: 860px;
}

@media (max-width: 959px) {
  .VPSidebar {
    display: none !important;
  }

  .VPContent.has-sidebar {
    padding-left: 0 !important;
  }
}

@media print {
  .VPSidebar,
  .VPDocAside,
  .VPDocFooter {
    display: none !important;
  }

  .VPContent.has-sidebar {
    padding-left: 0 !important;
  }
}
`;

const moduleLauncher = (module) => `#!/bin/zsh
cd "$(dirname "$0")"
port=8765
while lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; do
  port=$((port + 1))
done
open "http://127.0.0.1:$port/.routes/${module.route}/"
python3 -m http.server "$port" --bind 127.0.0.1 --directory "$PWD"
`;

const rootLauncher = `#!/bin/zsh
cd "$(dirname "$0")"
port=8750
while lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; do
  port=$((port + 1))
done
open "http://127.0.0.1:$port/"
python3 -m http.server "$port" --bind 127.0.0.1
`;

const copyTheme = async (docsDirectory) => {
  const sourceTheme = path.join(projectRoot, "docs", ".vitepress", "theme");
  const targetTheme = path.join(docsDirectory, ".vitepress", "theme");
  const sourceComponents = path.join(sourceTheme, "components");
  const targetComponents = path.join(targetTheme, "components");

  await mkdir(targetComponents, { recursive: true });
  await Promise.all([
    cp(path.join(sourceTheme, "style.css"), path.join(targetTheme, "style.css")),
    cp(
      path.join(sourceComponents, "ImageLightbox.vue"),
      path.join(targetComponents, "ImageLightbox.vue"),
    ),
    cp(
      path.join(sourceComponents, "imageZoom.ts"),
      path.join(targetComponents, "imageZoom.ts"),
    ),
    cp(
      path.join(sourceComponents, "MermaidDiagram.vue"),
      path.join(targetComponents, "MermaidDiagram.vue"),
    ),
  ]);
  await Promise.all([
    writeFile(path.join(targetTheme, "index.ts"), themeSource),
    writeFile(path.join(targetTheme, "modular.css"), modularCss),
  ]);
};

const prepareModuleSource = async (module, docsDirectory) => {
  if (module.kind === "case") {
    await cp(module.source, docsDirectory, { recursive: true });
    return;
  }

  await mkdir(docsDirectory, { recursive: true });
  const indexMarkdown = [
    `# ${module.title}`,
    "",
    ...module.chapters.map(
      (chapter) => `- [${chapter}](./${chapterRoute(chapter)}/)`,
    ),
    "",
  ].join("\n");
  await writeFile(path.join(docsDirectory, "index.md"), indexMarkdown);

  await Promise.all(
    module.chapters.map((chapter) =>
      cp(
        path.join(module.source, chapter),
        path.join(docsDirectory, chapterRoute(chapter)),
        { recursive: true },
      ),
    ),
  );
};

const listBuiltPages = async (directory) => {
  const entries = await readdir(directory, { withFileTypes: true });
  const pages = [];

  for (const entry of entries) {
    if (entry.name === ".routes") continue;
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) pages.push(...(await listBuiltPages(entryPath)));
    else if (entry.name === "index.html") pages.push(entryPath);
  }

  return pages;
};

const createLocalOpeningFiles = async (module, outputDirectory) => {
  const pages = await listBuiltPages(outputDirectory);
  const routePrefix = `/.routes/${module.route}/`;

  await Promise.all(
    pages.map(async (pagePath) => {
      const pageDirectory = path.dirname(pagePath);
      const relativeRoot = path.relative(pageDirectory, outputDirectory).split(path.sep).join("/") || ".";
      const localPrefix = relativeRoot === "." ? "./" : `${relativeRoot}/`;
      let html = await readFile(pagePath, "utf8");

      // 独立 HTML 通过相对路径加载 CSS、图片和视频，无需启动本地服务器。
      html = html.replaceAll(routePrefix, localPrefix);
      html = html.replaceAll('rel="preload stylesheet"', 'rel="stylesheet"');
      html = html.replace(/<link rel="modulepreload"[^>]*>\s*/g, "");
      html = html.replace(/<script\b[^>]*>[\s\S]*?<\/script>\s*/g, "");
      html = html.replace(/href="\.\/"/g, 'href="./打开课件.html"');
      html = html.replace(
        /href="((?:\.\.\/|\.\/)*)(chapter-\d+|extra-reading)\/"/g,
        'href="$1$2/打开课件.html"',
      );
      html = html.replace(
        "</head>",
        `<style>
          /* 本地双击版本：保留原课件排版，隐藏无法在 file:// 下工作的交互控件。 */
          .vp-doc .copy { display: none !important; }
          .VPDocFooter .prev-next { display: none !important; }
        </style>\n</head>`,
      );

      await writeFile(path.join(pageDirectory, "打开课件.html"), html);
    }),
  );
};

const buildModule = async (module, index) => {
  const stageDirectory = path.join(stagingRoot, String(index).padStart(2, "0"));
  const docsDirectory = path.join(stageDirectory, "docs");
  const configDirectory = path.join(docsDirectory, ".vitepress");
  const outputDirectory = path.join(outputRoot, module.folder);

  await rm(stageDirectory, { recursive: true, force: true });
  await mkdir(configDirectory, { recursive: true });
  await prepareModuleSource(module, docsDirectory);
  await Promise.all([
    cp(
      path.join(projectRoot, "docs", ".vitepress", "mermaid-markdown.ts"),
      path.join(configDirectory, "mermaid-markdown.ts"),
    ),
    writeFile(path.join(configDirectory, "config.mts"), configSource(module)),
    copyTheme(docsDirectory),
  ]);

  await execFileAsync(vitepressBin, ["build", docsDirectory, "--outDir", outputDirectory], {
    cwd: projectRoot,
    maxBuffer: 10 * 1024 * 1024,
  });

  // 保留原始 Markdown 与原始文件名素材，让每个模块可继续编辑且不会遗漏 HTML 视频资源。
  await cp(module.source, outputDirectory, { recursive: true });
  const launcherPath = path.join(outputDirectory, "打开本课件.command");
  const moduleReadme = `# ${module.title}\n\n类型：${module.kind === "collection" ? "整篇课件" : "独立案例"}\n\n双击“打开本课件.command”即可使用；网页、Markdown 原稿和原始素材均在本文件夹内。\n`;
  await Promise.all([
    writeFile(launcherPath, moduleLauncher(module)),
    writeFile(path.join(outputDirectory, "模块说明.md"), moduleReadme),
    mkdir(path.join(outputDirectory, ".routes"), { recursive: true }),
  ]);
  await symlink("..", path.join(outputDirectory, ".routes", module.route), "dir");
  await createLocalOpeningFiles(module, outputDirectory);
  await chmod(launcherPath, 0o755);

  return module;
};

const escapeHtml = (value) =>
  value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

const catalogHtml = () => {
  const cards = modules
    .map(
      (module) => `<a class="module module--${module.kind}" href=".routes/${module.route}/">
        <span class="module__type">${module.kind === "collection" ? "整篇模块" : "独立案例"}</span>
        <strong>${escapeHtml(module.title)}</strong>
        <span>打开课件 →</span>
      </a>`,
    )
    .join("\n");

  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>WorkBuddyGuide 散装课件</title>
  <style>
    :root { color: #172112; background: #f3f1e8; font-family: "Noto Sans SC", "PingFang SC", sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; }
    main { width: min(1160px, calc(100% - 40px)); margin: 0 auto; padding: 64px 0 80px; }
    header { border-bottom: 3px solid #172112; padding-bottom: 28px; margin-bottom: 32px; }
    .eyebrow { color: #49642a; font-size: 13px; font-weight: 800; letter-spacing: .14em; }
    h1 { max-width: 760px; margin: 10px 0 12px; font-family: Georgia, "Songti SC", serif; font-size: clamp(36px, 6vw, 70px); line-height: 1; }
    header p { max-width: 720px; margin: 0; color: #57604f; font-size: 17px; line-height: 1.8; }
    .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    .module { min-height: 190px; display: flex; flex-direction: column; justify-content: space-between; color: inherit; background: #fffdf6; border: 1px solid #c9c7ba; padding: 22px; text-decoration: none; transition: transform .18s ease, box-shadow .18s ease; }
    .module:hover { transform: translateY(-3px); box-shadow: 6px 6px 0 #172112; }
    .module--collection { background: #dff04f; border-color: #172112; }
    .module__type { width: fit-content; padding: 3px 7px; color: #526047; background: rgba(255,255,255,.66); border: 1px solid currentColor; font-size: 11px; font-weight: 800; letter-spacing: .08em; }
    .module strong { font-family: Georgia, "Songti SC", serif; font-size: 21px; line-height: 1.35; }
    .module > span:last-child { font-size: 13px; font-weight: 800; }
    @media (max-width: 860px) { .grid { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 560px) { main { width: min(100% - 24px, 1160px); padding-top: 36px; } .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <header>
      <div class="eyebrow">MODULAR COURSEWARE · 17 MODULES</div>
      <h1>WorkBuddyGuide<br />散装课件</h1>
      <p>第一篇与第四篇按整篇使用；第二篇、第三篇已逐章拆成独立案例。每个文件夹都可以单独复制、排列和授课。</p>
    </header>
    <section class="grid" aria-label="课件模块">${cards}</section>
  </main>
</body>
</html>`;
};

const readmeSource = `# WorkBuddyGuide 散装版使用说明

本目录由原始 \`WorkBuddyGuide\` 自动拆分，共 ${modules.length} 个可独立搬动的课件模块：

- 第一篇：1 个整篇模块，保留篇内章节目录。
- 第二篇：${secondChapters.length} 个独立案例，每章一个文件夹，无左侧导航。
- 第三篇：${thirdChapters.length} 个独立案例，每章一个文件夹，无左侧导航。
- 第四篇：1 个整篇模块，保留篇内章节目录。

## 使用方法

1. 双击根目录的“打开全部课件.command”，可查看全部模块。
2. 单独复制任一模块文件夹后，双击其中的“打开本课件.command”即可使用。
3. 每个模块同时包含网页课件、原始 Markdown 和原始图片/视频素材。
4. 网站级顶部导航、搜索、社区、GitHub 与编辑入口已从拆分版移除。

如需从最新原稿重新生成，请在 \`WorkBuddyGuide\` 项目中运行 \`npm run build:modular\`。重新生成会替换本目录。
`;

const manifest = {
  generatedAt: new Date().toISOString(),
  source: "WorkBuddyGuide/docs/bluebook",
  moduleCount: modules.length,
  modules: modules.map(({ folder, route, title, kind, chapters }) => ({
    folder,
    route,
    title,
    kind,
    chapterCount: chapters.length || 1,
  })),
};

const main = async () => {
  try {
    await stat(vitepressBin);
  } catch {
    throw new Error("未找到 VitePress，请先在 WorkBuddyGuide 中运行 npm install。 ");
  }

  await rm(outputRoot, { recursive: true, force: true });
  await rm(stagingRoot, { recursive: true, force: true });
  await mkdir(outputRoot, { recursive: true });

  // 限制并发数，避免多个包含 Mermaid 的构建同时占用过多内存。
  const queue = modules.map((module, index) => ({ module, index }));
  const worker = async () => {
    while (queue.length > 0) {
      const item = queue.shift();
      if (!item) return;
      process.stdout.write(`正在生成 ${item.module.folder}…\n`);
      await buildModule(item.module, item.index);
    }
  };
  await Promise.all([worker(), worker(), worker()]);

  const routeDirectory = path.join(outputRoot, ".routes");
  await mkdir(routeDirectory, { recursive: true });
  await Promise.all(
    modules.map((module) =>
      symlink(`../${module.folder}`, path.join(routeDirectory, module.route), "dir"),
    ),
  );

  const rootLauncherPath = path.join(outputRoot, "打开全部课件.command");
  await Promise.all([
    writeFile(path.join(outputRoot, "index.html"), catalogHtml()),
    writeFile(path.join(outputRoot, "README_使用说明.md"), readmeSource),
    writeFile(path.join(outputRoot, "modules.json"), `${json(manifest)}\n`),
    writeFile(rootLauncherPath, rootLauncher),
  ]);
  await chmod(rootLauncherPath, 0o755);
  await rm(stagingRoot, { recursive: true, force: true });

  process.stdout.write(`完成：${outputRoot}\n`);
};

await main();
