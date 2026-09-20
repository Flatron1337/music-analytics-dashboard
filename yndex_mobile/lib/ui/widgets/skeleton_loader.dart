import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';

/// Animated Shimmer Effect Widget that provides a fluid glowing gradient wave.
class ShimmerLoading extends StatefulWidget {
  final Widget child;

  const ShimmerLoading({super.key, required this.child});

  @override
  State<ShimmerLoading> createState() => _ShimmerLoadingState();
}

class _ShimmerLoadingState extends State<ShimmerLoading>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return ShaderMask(
          blendMode: BlendMode.srcATop,
          shaderCallback: (bounds) {
            final double progress = _controller.value;
            // Sweep gradient from left to right
            return LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: const [
                Color(0xFF1E222A),
                Color(0xFF2E3544),
                Color(0xFF1E222A),
              ],
              stops: [
                (progress - 0.3).clamp(0.0, 1.0),
                progress.clamp(0.0, 1.0),
                (progress + 0.3).clamp(0.0, 1.0),
              ],
            ).createShader(bounds);
          },
          child: widget.child,
        );
      },
      child: widget.child,
    );
  }
}

/// Generic skeleton block with custom dimensions and border radius.
class SkeletonBox extends StatelessWidget {
  final double? width;
  final double? height;
  final double borderRadius;

  const SkeletonBox({
    super.key,
    this.width,
    this.height,
    this.borderRadius = 8,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: AppColors.surfaceElevated,
        borderRadius: BorderRadius.circular(borderRadius),
      ),
    );
  }
}

/// Skeleton placeholder for the Overview Tab
class OverviewSkeleton extends StatelessWidget {
  const OverviewSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return ShimmerLoading(
      child: ListView(
        physics: const NeverScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          // Header placeholder
          const SkeletonBox(width: 180, height: 26, borderRadius: 6),
          const SizedBox(height: 8),
          const SkeletonBox(width: 130, height: 14, borderRadius: 4),
          const SizedBox(height: 24),

          // 4 Metric cards (2x2 grid)
          Row(
            children: const [
              Expanded(child: SkeletonBox(height: 100, borderRadius: 16)),
              SizedBox(width: 12),
              Expanded(child: SkeletonBox(height: 100, borderRadius: 16)),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: const [
              Expanded(child: SkeletonBox(height: 100, borderRadius: 16)),
              SizedBox(width: 12),
              Expanded(child: SkeletonBox(height: 100, borderRadius: 16)),
            ],
          ),
          const SizedBox(height: 24),

          // Top Artists Card Placeholder
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SkeletonBox(width: 160, height: 20, borderRadius: 6),
                const SizedBox(height: 16),
                for (int i = 0; i < 5; i++) ...[
                  Row(
                    children: [
                      const SkeletonBox(width: 24, height: 24, borderRadius: 12),
                      const SizedBox(width: 12),
                      Expanded(
                        child: SkeletonBox(
                          width: double.infinity,
                          height: 16,
                          borderRadius: 4,
                        ),
                      ),
                      const SizedBox(width: 16),
                      const SkeletonBox(width: 40, height: 16, borderRadius: 4),
                    ],
                  ),
                  if (i < 4) const SizedBox(height: 12),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Collab ratio placeholder
          const SkeletonBox(height: 80, borderRadius: 16),
        ],
      ),
    );
  }
}

/// Skeleton placeholder for the Genres Tab
class GenresSkeleton extends StatelessWidget {
  const GenresSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return ShimmerLoading(
      child: ListView(
        physics: const NeverScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          const SkeletonBox(width: 180, height: 26, borderRadius: 6),
          const SizedBox(height: 8),
          const SkeletonBox(width: 220, height: 14, borderRadius: 4),
          const SizedBox(height: 24),

          // Circle pie chart placeholder
          Center(
            child: Container(
              width: 180,
              height: 180,
              decoration: const BoxDecoration(
                color: AppColors.surfaceElevated,
                shape: BoxShape.circle,
              ),
            ),
          ),
          const SizedBox(height: 32),

          // Genre clusters cards
          for (int i = 0; i < 5; i++) ...[
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Row(
                children: const [
                  SkeletonBox(width: 36, height: 36, borderRadius: 10),
                  SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        SkeletonBox(width: 120, height: 16, borderRadius: 4),
                        SizedBox(height: 6),
                        SkeletonBox(width: 60, height: 12, borderRadius: 3),
                      ],
                    ),
                  ),
                  SkeletonBox(width: 44, height: 20, borderRadius: 6),
                ],
              ),
            ),
            const SizedBox(height: 10),
          ],
        ],
      ),
    );
  }
}

/// Skeleton placeholder for the Tracks Tab
class TracksSkeleton extends StatelessWidget {
  const TracksSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return ShimmerLoading(
      child: ListView.builder(
        physics: const NeverScrollableScrollPhysics(),
        itemCount: 8,
        itemBuilder: (context, index) {
          return Container(
            margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Row(
              children: [
                // Album cover square
                const SkeletonBox(width: 50, height: 50, borderRadius: 8),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      SkeletonBox(width: 180, height: 16, borderRadius: 4),
                      SizedBox(height: 6),
                      SkeletonBox(width: 110, height: 12, borderRadius: 3),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                const SkeletonBox(width: 42, height: 16, borderRadius: 6),
              ],
            ),
          );
        },
      ),
    );
  }
}

/// Skeleton placeholder for the Timeline Tab
class TimelineSkeleton extends StatelessWidget {
  const TimelineSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return ShimmerLoading(
      child: ListView(
        physics: const NeverScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          const SkeletonBox(width: 180, height: 26, borderRadius: 6),
          const SizedBox(height: 8),
          const SkeletonBox(width: 240, height: 14, borderRadius: 4),
          const SizedBox(height: 24),

          for (int i = 0; i < 4; i++) ...[
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      SkeletonBox(width: 90, height: 18, borderRadius: 4),
                      SkeletonBox(width: 60, height: 16, borderRadius: 6),
                    ],
                  ),
                  SizedBox(height: 14),
                  SkeletonBox(height: 20, borderRadius: 6),
                ],
              ),
            ),
            const SizedBox(height: 14),
          ],
        ],
      ),
    );
  }
}
