import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';
import codeImport from 'remark-code-import';
import path from 'path';

const config: Config = {
  title: 'AP2 from First Principles',
  tagline: 'Learn the Agent Payments Protocol by building it, then mapping to the SDK.',
  favicon: 'img/favicon.ico',
  url: 'https://ap2-getting-started.vercel.app',
  baseUrl: '/',
  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',
  i18n: {defaultLocale: 'en', locales: ['en']},
  presets: [
    [
      'classic',
      {
        docs: {
          routeBasePath: 'docs',
          sidebarPath: './sidebars.ts',
          remarkPlugins: [
            [
              codeImport,
              {
                allowImportingFromOutside: true,
                rootDir: path.resolve(__dirname, '..'),
              },
            ],
          ],
        },
        blog: {showReadingTime: true},
        theme: {customCss: './src/css/custom.css'},
      } satisfies Preset.Options,
    ],
  ],
  themeConfig: {
    navbar: {
      title: 'AP2 from First Principles',
      items: [
        {type: 'docSidebar', sidebarId: 'lessons', position: 'left', label: 'Lessons'},
        {to: '/roadmap', label: 'Roadmap', position: 'left'},
        {to: '/glossary', label: 'Glossary', position: 'left'},
        {to: '/blog', label: 'Blog', position: 'left'},
        {
          href: 'https://github.com/google-agentic-commerce/AP2',
          label: 'AP2 spec',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Learn',
          items: [
            {label: 'Lessons', to: '/docs/why-agent-payments'},
            {label: 'Roadmap', to: '/roadmap'},
            {label: 'Glossary', to: '/glossary'},
          ],
        },
        {
          title: 'AP2',
          items: [
            {label: 'Official repo', href: 'https://github.com/google-agentic-commerce/AP2'},
            {label: 'Intro video', href: 'https://youtu.be/jSHj0z9Gi24'},
          ],
        },
      ],
      copyright: `Built ${new Date().getFullYear()} as a public learning resource.`,
    },
    prism: {theme: prismThemes.github, darkTheme: prismThemes.dracula},
  } satisfies Preset.ThemeConfig,
};

export default config;
