import type { ArticleWordCounts, NovelWordCounts } from "./types";

export const defaultNovelWordCounts: NovelWordCounts = {
  small_summary_word_count: "10000-12000",
  small_plot_word_count: "10000-12000",
  small_char_word_count: "10000-12000",
  big_plot_word_count: "10000-12000",
  big_char_word_count: "10000-12000",
  super_plot_p1_word_count: "20000-25000",
  super_plot_p2_word_count: "20000-30000",
  super_char_p1_word_count: "25000",
  super_char_p2_word_count: "15000-20000",
  ultimate_plot_p1_word_count: "20000-25000",
  ultimate_plot_p2_word_count: "20000-30000",
  ultimate_char_p1_word_count: "25000",
  ultimate_char_p2_word_count: "15000-20000"
};

export const defaultArticleWordCounts: ArticleWordCounts = {
  section: "3000-4000",
  final: "8000-10000"
};
