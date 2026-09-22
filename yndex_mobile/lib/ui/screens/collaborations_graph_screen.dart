import 'dart:math';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../data/models/collab_graph.dart';
import '../../data/services/api_service.dart';
import 'artist_detail_screen.dart';

class CollaborationsGraphScreen extends StatefulWidget {
  final ApiService apiService;
  final String? initialFocusArtist;

  const CollaborationsGraphScreen({
    super.key,
    required this.apiService,
    this.initialFocusArtist,
  });

  static void navigate(
    BuildContext context,
    ApiService apiService, {
    String? focusArtist,
  }) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => CollaborationsGraphScreen(
          apiService: apiService,
          initialFocusArtist: focusArtist,
        ),
      ),
    );
  }

  @override
  State<CollaborationsGraphScreen> createState() =>
      _CollaborationsGraphScreenState();
}

class _CollaborationsGraphScreenState extends State<CollaborationsGraphScreen> {
  static const double _canvasSize = 2400.0;
  static const double _canvasCenter = _canvasSize / 2;
  static const double _scaleFactor = 900.0;

  late final TransformationController _transformController;
  CollabGraphData? _graphData;
  bool _isLoading = true;
  String? _error;

  int _minCollabs = 1;
  int _limitNodes = 60;
  String? _focusArtist;

  GraphNode? _selectedNode;
  final Set<String> _connectedNodeIds = {};

  @override
  void initState() {
    super.initState();
    _focusArtist = widget.initialFocusArtist;
    _transformController = TransformationController();

    // Center the initial view
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _centerView();
    });

    _loadGraph();
  }

  void _centerView() {
    final screenSize = MediaQuery.of(context).size;
    const initialScale = 0.55;
    final xTranslation = (screenSize.width - (_canvasSize * initialScale)) / 2;
    final yTranslation = (screenSize.height - (_canvasSize * initialScale)) / 2;

    _transformController.value = Matrix4(
      initialScale, 0, 0, 0,
      0, initialScale, 0, 0,
      0, 0, 1, 0,
      xTranslation, yTranslation, 0, 1,
    );
  }

  Future<void> _exportHtmlGraph() async {
    try {
      final exportUrl = await widget.apiService.getGraphExportHtmlUrl(
        minCollabs: _minCollabs,
        limitNodes: _limitNodes,
      );
      final uri = Uri.parse(exportUrl);
      final launched = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!launched) {
        await launchUrl(uri, mode: LaunchMode.platformDefault);
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Интерактивная карта связей (HTML) успешно скачана!'),
            backgroundColor: Color(0xFF1E1B4B),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка экспорта: $e')),
        );
      }
    }
  }

  Future<void> _loadGraph() async {
    setState(() {
      _isLoading = true;
      _error = null;
      _selectedNode = null;
      _connectedNodeIds.clear();
    });

    try {
      final data = await widget.apiService.fetchCollaborationsGraph(
        minCollabs: _minCollabs,
        limitNodes: _limitNodes,
        focusArtist: _focusArtist,
      );
      if (!mounted) return;
      setState(() {
        _graphData = data;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  void _selectNode(GraphNode? node) {
    setState(() {
      _selectedNode = node;
      _connectedNodeIds.clear();
      if (node != null && _graphData != null) {
        _connectedNodeIds.add(node.id);
        for (final edge in _graphData!.edges) {
          if (edge.source == node.id) {
            _connectedNodeIds.add(edge.target);
          } else if (edge.target == node.id) {
            _connectedNodeIds.add(edge.source);
          }
        }
      }
    });
  }

  Offset _nodeToCanvas(GraphNode node) {
    return Offset(
      _canvasCenter + (node.x * _scaleFactor),
      _canvasCenter + (node.y * _scaleFactor),
    );
  }

  void _handleCanvasTap(TapUpDetails details) {
    if (_graphData == null) return;

    final tapPos = details.localPosition;
    GraphNode? closest;
    double minDistance = double.infinity;

    for (final node in _graphData!.nodes) {
      final nodePos = _nodeToCanvas(node);
      final dist = (tapPos - nodePos).distance;
      final nodeRadius = _calculateNodeRadius(node);

      if (dist <= nodeRadius + 18.0 && dist < minDistance) {
        minDistance = dist;
        closest = node;
      }
    }

    _selectNode(closest);
  }

  double _calculateNodeRadius(GraphNode node) {
    return (12.0 + (sqrt(node.tracksCount) * 2.8) + (node.degree * 0.4))
        .clamp(14.0, 44.0);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF090D14),
      body: Stack(
        children: [
          // Background ambient gradient
          Positioned.fill(
            child: Container(
              decoration: const BoxDecoration(
                gradient: RadialGradient(
                  center: Alignment.center,
                  radius: 1.2,
                  colors: [
                    Color(0xFF141C2B),
                    Color(0xFF090D14),
                  ],
                ),
              ),
            ),
          ),

          // Main Graph Canvas
          if (_isLoading)
            const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  CircularProgressIndicator(
                    color: Color(0xFF00E5FF),
                    strokeWidth: 2.5,
                  ),
                  SizedBox(height: 16),
                  Text(
                    'Построение графа связей...',
                    style: TextStyle(color: Colors.white70, fontSize: 14),
                  ),
                ],
              ),
            )
          else if (_error != null)
            Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.error_outline, color: Colors.redAccent, size: 48),
                    const SizedBox(height: 12),
                    Text(
                      _error!,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.white70),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton.icon(
                      onPressed: _loadGraph,
                      icon: const Icon(Icons.refresh),
                      label: const Text('Повторить'),
                    ),
                  ],
                ),
              ),
            )
          else if (_graphData != null && _graphData!.nodes.isEmpty)
            Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.hub_outlined, color: Colors.white38, size: 48),
                  const SizedBox(height: 12),
                  const Text(
                    'Связей по выбранным критериям не найдено',
                    style: TextStyle(color: Colors.white70),
                  ),
                  const SizedBox(height: 12),
                  TextButton(
                    onPressed: () {
                      setState(() {
                        _minCollabs = 1;
                        _focusArtist = null;
                      });
                      _loadGraph();
                    },
                    child: const Text('Сбросить фильтры'),
                  ),
                ],
              ),
            )
          else if (_graphData != null)
            Positioned.fill(
              child: InteractiveViewer(
                transformationController: _transformController,
                minScale: 0.2,
                maxScale: 3.5,
                boundaryMargin: const EdgeInsets.all(800),
                constrained: false,
                child: GestureDetector(
                  onTapUp: _handleCanvasTap,
                  child: Container(
                    width: _canvasSize,
                    height: _canvasSize,
                    color: Colors.transparent,
                    child: CustomPaint(
                      size: const Size(_canvasSize, _canvasSize),
                      painter: _CollabGraphPainter(
                        graphData: _graphData!,
                        scaleFactor: _scaleFactor,
                        canvasCenter: _canvasCenter,
                        selectedNode: _selectedNode,
                        connectedNodeIds: _connectedNodeIds,
                      ),
                    ),
                  ),
                ),
              ),
            ),

          // Top App Bar and Filters overlay
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: _buildTopOverlay(),
          ),

          // Bottom Node Inspector Card
          if (_selectedNode != null)
            Positioned(
              bottom: 24,
              left: 16,
              right: 16,
              child: _buildSelectedNodeSheet(_selectedNode!),
            ),
        ],
      ),
    );
  }

  Widget _buildTopOverlay() {
    final hasFocus = _focusArtist != null && _focusArtist!.isNotEmpty;

    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            const Color(0xFF090D14).withValues(alpha: 0.95),
            const Color(0xFF090D14).withValues(alpha: 0.7),
            Colors.transparent,
          ],
        ),
      ),
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              // Header Row
              Row(
                children: [
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.arrow_back_ios_new, color: Colors.white, size: 20),
                    style: IconButton.styleFrom(
                      backgroundColor: Colors.white.withValues(alpha: 0.08),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Text(
                              'Граф связей артистов',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(width: 6),
                            const Text('🕸️', style: TextStyle(fontSize: 16)),
                          ],
                        ),
                        if (_graphData != null)
                          Text(
                            hasFocus
                                ? 'Фокус: $_focusArtist • ${_graphData!.totalNodes} артистов'
                                : '${_graphData!.totalNodes} артистов • ${_graphData!.totalEdges} совместных связей',
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.6),
                              fontSize: 12,
                            ),
                          ),
                      ],
                    ),
                  ),
                  IconButton(
                    onPressed: _exportHtmlGraph,
                    tooltip: 'Экспорт интерактивной карты в HTML',
                    icon: const Icon(Icons.download_rounded, color: Color(0xFFD500F9)),
                    style: IconButton.styleFrom(
                      backgroundColor: const Color(0xFFD500F9).withValues(alpha: 0.12),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    onPressed: _centerView,
                    tooltip: 'Центрировать карту',
                    icon: const Icon(Icons.filter_center_focus, color: Color(0xFF00E5FF)),
                    style: IconButton.styleFrom(
                      backgroundColor: const Color(0xFF00E5FF).withValues(alpha: 0.1),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),

              // Filter Chips Row
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    if (hasFocus) ...[
                      InputChip(
                        label: Text('Фокус: $_focusArtist'),
                        labelStyle: const TextStyle(
                          color: Color(0xFF00E5FF),
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                        ),
                        backgroundColor: const Color(0xFF00E5FF).withValues(alpha: 0.15),
                        onDeleted: () {
                          setState(() {
                            _focusArtist = null;
                          });
                          _loadGraph();
                        },
                        deleteIconColor: const Color(0xFF00E5FF),
                      ),
                      const SizedBox(width: 8),
                    ],

                    _buildFilterChip(
                      label: '1+ фит',
                      isSelected: _minCollabs == 1,
                      onTap: () {
                        if (_minCollabs != 1) {
                          setState(() => _minCollabs = 1);
                          _loadGraph();
                        }
                      },
                    ),
                    const SizedBox(width: 6),
                    _buildFilterChip(
                      label: '2+ фита',
                      isSelected: _minCollabs == 2,
                      onTap: () {
                        if (_minCollabs != 2) {
                          setState(() => _minCollabs = 2);
                          _loadGraph();
                        }
                      },
                    ),
                    const SizedBox(width: 6),
                    _buildFilterChip(
                      label: '3+ фитов',
                      isSelected: _minCollabs == 3,
                      onTap: () {
                        if (_minCollabs != 3) {
                          setState(() => _minCollabs = 3);
                          _loadGraph();
                        }
                      },
                    ),
                    const SizedBox(width: 12),
                    Container(width: 1, height: 16, color: Colors.white24),
                    const SizedBox(width: 12),

                    _buildFilterChip(
                      label: 'Топ-40',
                      isSelected: _limitNodes == 40,
                      onTap: () {
                        if (_limitNodes != 40) {
                          setState(() => _limitNodes = 40);
                          _loadGraph();
                        }
                      },
                    ),
                    const SizedBox(width: 6),
                    _buildFilterChip(
                      label: 'Топ-60',
                      isSelected: _limitNodes == 60,
                      onTap: () {
                        if (_limitNodes != 60) {
                          setState(() => _limitNodes = 60);
                          _loadGraph();
                        }
                      },
                    ),
                    const SizedBox(width: 6),
                    _buildFilterChip(
                      label: 'Топ-90',
                      isSelected: _limitNodes == 90,
                      onTap: () {
                        if (_limitNodes != 90) {
                          setState(() => _limitNodes = 90);
                          _loadGraph();
                        }
                      },
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFilterChip({
    required String label,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: isSelected
              ? const Color(0xFF00E5FF).withValues(alpha: 0.2)
              : Colors.white.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected
                ? const Color(0xFF00E5FF)
                : Colors.white.withValues(alpha: 0.12),
            width: 1,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isSelected ? const Color(0xFF00E5FF) : Colors.white70,
            fontSize: 11,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
          ),
        ),
      ),
    );
  }

  Widget _buildSelectedNodeSheet(GraphNode node) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF161B22).withValues(alpha: 0.96),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: node.color.withValues(alpha: 0.6), width: 1.5),
        boxShadow: [
          BoxShadow(
            color: node.color.withValues(alpha: 0.25),
            blurRadius: 25,
            spreadRadius: 2,
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 14,
                height: 14,
                decoration: BoxDecoration(
                  color: node.color,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: node.color.withValues(alpha: 0.8),
                      blurRadius: 6,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  node.name,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 17,
                    fontWeight: FontWeight.bold,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              IconButton(
                onPressed: () => _selectNode(null),
                icon: const Icon(Icons.close, color: Colors.white54, size: 20),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
              ),
            ],
          ),
          const SizedBox(height: 10),

          // Stats Chips
          Row(
            children: [
              _buildBadge(
                label: node.dominantGenre,
                color: node.color,
              ),
              const SizedBox(width: 8),
              _buildBadge(
                label: '${node.tracksCount} треков',
                color: Colors.white70,
              ),
              const SizedBox(width: 8),
              _buildBadge(
                label: '${node.degree} фитов',
                color: const Color(0xFF00E5FF),
              ),
            ],
          ),
          const SizedBox(height: 14),

          // Action Buttons
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () {
                    setState(() {
                      _focusArtist = node.name;
                    });
                    _loadGraph();
                  },
                  icon: const Icon(Icons.center_focus_strong, size: 16),
                  label: const Text('Фокус на связях'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFF00E5FF),
                    side: const BorderSide(color: Color(0xFF00E5FF)),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: () {
                    ArtistDetailScreen.navigate(
                      context,
                      node.name,
                      widget.apiService,
                    );
                  },
                  icon: const Icon(Icons.person, size: 16),
                  label: const Text('Подробнее'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: node.color,
                    foregroundColor: Colors.black,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    elevation: 0,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildBadge({required String label, required Color color}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.3), width: 0.8),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class _CollabGraphPainter extends CustomPainter {
  final CollabGraphData graphData;
  final double scaleFactor;
  final double canvasCenter;
  final GraphNode? selectedNode;
  final Set<String> connectedNodeIds;

  _CollabGraphPainter({
    required this.graphData,
    required this.scaleFactor,
    required this.canvasCenter,
    this.selectedNode,
    required this.connectedNodeIds,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // 1. Map nodes to positions
    final nodePosMap = <String, Offset>{};
    final nodeMap = <String, GraphNode>{};

    for (final node in graphData.nodes) {
      final pos = Offset(
        canvasCenter + (node.x * scaleFactor),
        canvasCenter + (node.y * scaleFactor),
      );
      nodePosMap[node.id] = pos;
      nodeMap[node.id] = node;
    }

    final hasSelection = selectedNode != null;

    // 2. Draw Edges
    for (final edge in graphData.edges) {
      final p1 = nodePosMap[edge.source];
      final p2 = nodePosMap[edge.target];
      if (p1 == null || p2 == null) continue;

      final isIncident = hasSelection &&
          (edge.source == selectedNode!.id || edge.target == selectedNode!.id);

      final isConnectedContext =
          hasSelection && (connectedNodeIds.contains(edge.source) && connectedNodeIds.contains(edge.target));

      final double strokeWidth = (1.2 + (edge.weight * 0.7)).clamp(1.2, 5.5);

      final paint = Paint()
        ..strokeWidth = isIncident ? strokeWidth * 1.5 : strokeWidth
        ..style = PaintingStyle.stroke;

      if (isIncident) {
        paint.color = const Color(0xFF00E5FF).withValues(alpha: 0.9);
      } else if (hasSelection) {
        paint.color = isConnectedContext
            ? Colors.white.withValues(alpha: 0.2)
            : Colors.white.withValues(alpha: 0.04);
      } else {
        paint.color = const Color(0xFF38495E).withValues(alpha: 0.45);
      }

      canvas.drawLine(p1, p2, paint);
    }

    // 3. Draw Nodes and Labels
    final textPainter = TextPainter(textDirection: TextDirection.ltr);

    for (final node in graphData.nodes) {
      final pos = nodePosMap[node.id]!;
      final radius = (12.0 + (sqrt(node.tracksCount) * 2.8) + (node.degree * 0.4))
          .clamp(14.0, 44.0);

      final isSelected = selectedNode?.id == node.id;
      final isConnected = connectedNodeIds.contains(node.id);

      double opacity = 1.0;
      if (hasSelection && !isConnected) {
        opacity = 0.22;
      }

      // Outer glow
      final glowPaint = Paint()
        ..color = node.color.withValues(alpha: isSelected ? 0.7 : 0.25 * opacity)
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, isSelected ? 16.0 : 8.0);
      canvas.drawCircle(pos, radius + (isSelected ? 6.0 : 3.0), glowPaint);

      // Node Body Circle
      final bodyPaint = Paint()
        ..color = node.color.withValues(alpha: opacity)
        ..style = PaintingStyle.fill;
      canvas.drawCircle(pos, radius, bodyPaint);

      // Inner Core Accent
      final corePaint = Paint()
        ..color = Colors.white.withValues(alpha: isSelected ? 0.9 : 0.35 * opacity)
        ..style = PaintingStyle.stroke
        ..strokeWidth = isSelected ? 2.5 : 1.5;
      canvas.drawCircle(pos, radius * 0.75, corePaint);

      // Node Label Text (Always clear with dark outline)
      final labelStyle = TextStyle(
        color: Colors.white.withValues(alpha: hasSelection && !isConnected ? 0.25 : 0.95),
        fontSize: radius > 22 ? 12 : 11,
        fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
        shadows: const [
          Shadow(color: Colors.black, blurRadius: 4, offset: Offset(0, 1)),
          Shadow(color: Colors.black, blurRadius: 8),
        ],
      );

      textPainter.text = TextSpan(text: node.name, style: labelStyle);
      textPainter.layout(maxWidth: 160);
      textPainter.paint(
        canvas,
        Offset(pos.dx - (textPainter.width / 2), pos.dy + radius + 4),
      );
    }
  }

  @override
  bool shouldRepaint(covariant _CollabGraphPainter oldDelegate) {
    return oldDelegate.graphData != graphData ||
        oldDelegate.selectedNode != selectedNode ||
        oldDelegate.connectedNodeIds != connectedNodeIds;
  }
}
