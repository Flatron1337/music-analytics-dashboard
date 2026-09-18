import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../data/models/genre_cluster.dart';

class GenrePieChart extends StatefulWidget {
  final List<GenreCluster> clusters;
  final Function(GenreCluster?)? onSelectCluster;

  const GenrePieChart({
    super.key,
    required this.clusters,
    this.onSelectCluster,
  });

  @override
  State<GenrePieChart> createState() => _GenrePieChartState();
}

class _GenrePieChartState extends State<GenrePieChart> {
  int _touchedIndex = -1;

  @override
  Widget build(BuildContext context) {
    if (widget.clusters.isEmpty) {
      return const SizedBox(
        height: 220,
        child: Center(child: Text('Нет данных по жанрам')),
      );
    }

    return SizedBox(
      height: 240,
      child: Stack(
        alignment: Alignment.center,
        children: [
          PieChart(
            PieChartData(
              pieTouchData: PieTouchData(
                touchCallback: (FlTouchEvent event, pieTouchResponse) {
                  setState(() {
                    if (!event.isInterestedForInteractions ||
                        pieTouchResponse == null ||
                        pieTouchResponse.touchedSection == null) {
                      _touchedIndex = -1;
                      widget.onSelectCluster?.call(null);
                      return;
                    }
                    _touchedIndex = pieTouchResponse.touchedSection!.touchedSectionIndex;
                    if (_touchedIndex >= 0 && _touchedIndex < widget.clusters.length) {
                      widget.onSelectCluster?.call(widget.clusters[_touchedIndex]);
                    }
                  });
                },
              ),
              borderData: FlBorderData(show: false),
              sectionsSpace: 3,
              centerSpaceRadius: 65,
              sections: _buildSections(),
            ),
          ),
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                _touchedIndex >= 0 && _touchedIndex < widget.clusters.length
                    ? '${widget.clusters[_touchedIndex].percent}%'
                    : '${widget.clusters.length}',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                  color: _touchedIndex >= 0 && _touchedIndex < widget.clusters.length
                      ? widget.clusters[_touchedIndex].color
                      : AppColors.textPrimary,
                ),
              ),
              Text(
                _touchedIndex >= 0 && _touchedIndex < widget.clusters.length
                    ? widget.clusters[_touchedIndex].name
                    : 'Кластеров',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppColors.textSecondary,
                  fontWeight: FontWeight.w500,
                ),
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ],
      ),
    );
  }

  List<PieChartSectionData> _buildSections() {
    return List.generate(widget.clusters.length, (i) {
      final isTouched = i == _touchedIndex;
      final cluster = widget.clusters[i];
      final radius = isTouched ? 36.0 : 28.0;

      return PieChartSectionData(
        color: cluster.color,
        value: cluster.percent > 0 ? cluster.percent : 0.1,
        title: isTouched ? '${cluster.percent}%' : '',
        radius: radius,
        titleStyle: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.bold,
          color: Colors.black,
        ),
      );
    });
  }
}
