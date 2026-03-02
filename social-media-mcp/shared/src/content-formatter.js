/**
 * Content Formatter for Social Media Posts
 * Handles character limits, hashtag formatting, and platform-specific optimizations
 */

/**
 * Platform-specific limits and configurations
 */
export const PLATFORM_LIMITS = {
  facebook: {
    message: 63206,
    hashtags: 30,
    linkPreview: true,
    supportsThreads: false
  },
  instagram: {
    caption: 2200,
    hashtags: 30,
    bio: 150,
    supportsThreads: false,
    supportsReels: true,
    supportsStories: true
  },
  twitter: {
    tweet: 280,
    thread: 25000,
    hashtags: 30,
    pollOptions: 4,
    pollDuration: 10080, // 7 days in minutes
    supportsThreads: true
  }
};

/**
 * Truncate text to specified length with ellipsis
 */
export function truncate(text, maxLength, ellipsis = '...') {
  if (!text || text.length <= maxLength) return text;
  return text.substring(0, maxLength - ellipsis.length) + ellipsis;
}

/**
 * Count hashtags in text
 */
export function countHashtags(text) {
  if (!text) return 0;
  const matches = text.match(/#[\w\u00C0-\u017F]+/g);
  return matches ? matches.length : 0;
}

/**
 * Extract hashtags from text
 */
export function extractHashtags(text) {
  if (!text) return [];
  const matches = text.match(/#[\w\u00C0-\u017F]+/g);
  return matches ? matches.map(h => h.substring(1)) : [];
}

/**
 * Remove hashtags from text
 */
export function removeHashtags(text) {
  if (!text) return text;
  return text.replace(/#[\w\u00C0-\u017F]+/g, '').trim();
}

/**
 * Format hashtags for a specific platform
 */
export function formatHashtags(hashtags, platform, maxCount = 30) {
  if (!hashtags || hashtags.length === 0) return '';
  
  const limited = hashtags.slice(0, maxCount);
  
  switch (platform) {
    case 'instagram':
      // Instagram: hashtags can be at end or in comments
      return limited.map(h => h.startsWith('#') ? h : `#${h}`).join(' ');
    case 'twitter':
      // Twitter: integrate into tweet naturally
      return limited.map(h => h.startsWith('#') ? h : `#${h}`).join(' ');
    case 'facebook':
      // Facebook: fewer hashtags typically used
      return limited.slice(0, 5).map(h => h.startsWith('#') ? h : `#${h}`).join(' ');
    default:
      return limited.map(h => h.startsWith('#') ? h : `#${h}`).join(' ');
  }
}

/**
 * Optimize content for platform
 */
export function optimizeForPlatform(content, platform) {
  const limits = PLATFORM_LIMITS[platform];
  if (!limits) return content;

  let optimized = { ...content };

  // Handle message/caption truncation
  if (optimized.message && limits.message) {
    optimized.message = truncate(optimized.message, limits.message);
  }
  if (optimized.caption && limits.caption) {
    optimized.caption = truncate(optimized.caption, limits.caption);
  }
  if (optimized.text && limits.tweet) {
    optimized.text = truncate(optimized.text, limits.tweet);
  }

  // Handle hashtags
  if (optimized.hashtags && limits.hashtags) {
    optimized.hashtags = optimized.hashtags.slice(0, limits.hashtags);
  }

  // Platform-specific optimizations
  if (platform === 'twitter') {
    // Twitter: suggest thread if too long
    if (content.text && content.text.length > limits.tweet) {
      optimized.suggestThread = true;
    }
  }

  if (platform === 'instagram') {
    // Instagram: suggest line breaks for readability
    if (optimized.caption) {
      optimized.caption = optimized.caption.replace(/\n{3,}/g, '\n\n');
    }
  }

  return optimized;
}

/**
 * Generate platform-specific variations of content
 */
export function generateVariations(baseContent, platforms) {
  const variations = {};

  for (const platform of platforms) {
    variations[platform] = optimizeForPlatform(baseContent, platform);
  }

  return variations;
}

/**
 * Validate content for platform
 */
export function validateContent(content, platform) {
  const limits = PLATFORM_LIMITS[platform];
  const errors = [];
  const warnings = [];

  if (!limits) {
    errors.push(`Unknown platform: ${platform}`);
    return { valid: false, errors, warnings };
  }

  // Check message/caption length
  const textLength = content.message?.length || content.caption?.length || content.text?.length || 0;
  const maxTextLength = limits.message || limits.caption || limits.tweet;
  
  if (textLength > maxTextLength) {
    errors.push(`Text too long: ${textLength} > ${maxTextLength} characters`);
  } else if (textLength > maxTextLength * 0.9) {
    warnings.push(`Text approaching limit: ${textLength}/${maxTextLength} characters`);
  }

  // Check hashtag count
  if (content.hashtags && content.hashtags.length > limits.hashtags) {
    errors.push(`Too many hashtags: ${content.hashtags.length} > ${limits.hashtags}`);
  }

  // Twitter-specific validation
  if (platform === 'twitter') {
    if (content.poll) {
      if (content.poll.options.length > limits.pollOptions) {
        errors.push(`Too many poll options: ${content.poll.options.length} > ${limits.pollOptions}`);
      }
      if (content.poll.durationMinutes > limits.pollDuration) {
        errors.push(`Poll duration too long: ${content.poll.durationMinutes} > ${limits.pollDuration} minutes`);
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings
  };
}

/**
 * Calculate estimated engagement score based on content features
 */
export function estimateEngagement(content, platform) {
  let score = 50; // Base score

  // Hashtag bonus
  const hashtagCount = countHashtags(content.message || content.caption || content.text || '');
  if (platform === 'instagram') {
    score += Math.min(hashtagCount * 2, 30); // Up to 30 points for hashtags
  } else if (platform === 'twitter') {
    score += Math.min(hashtagCount * 3, 15); // Up to 15 points for hashtags
  }

  // Media bonus
  if (content.mediaUrls?.length > 0 || content.picture || content.mediaUrl) {
    score += 15;
  }

  // Link penalty (sometimes reduces engagement)
  if (content.link || content.url) {
    score -= 5;
  }

  // Length optimization
  const textLength = (content.message || content.caption || content.text || '').length;
  if (platform === 'twitter' && textLength > 100 && textLength < 280) {
    score += 10; // Longer tweets often perform better
  }

  // Question bonus (encourages engagement)
  const text = content.message || content.caption || content.text || '';
  if (text.includes('?')) {
    score += 10;
  }

  return Math.min(Math.max(score, 0), 100); // Clamp to 0-100
}

export default {
  PLATFORM_LIMITS,
  truncate,
  countHashtags,
  extractHashtags,
  removeHashtags,
  formatHashtags,
  optimizeForPlatform,
  generateVariations,
  validateContent,
  estimateEngagement
};
