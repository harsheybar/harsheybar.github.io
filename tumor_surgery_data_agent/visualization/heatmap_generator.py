"""
Heatmap Generator

Creates geographic heatmaps showing surgical volume density and coldspots.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    logger.warning("Plotly not available. Install with: pip install plotly")
    PLOTLY_AVAILABLE = False

try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except ImportError:
    logger.warning("GeoPandas not available. Install with: pip install geopandas")
    GEOPANDAS_AVAILABLE = False


class HeatmapGenerator:
    """
    Generates heatmaps and visualizations for surgical volume and coldspot analysis.
    """

    def __init__(self):
        """Initialize heatmap generator."""
        self.color_scale_coldspot = ['#2ecc71', '#f39c12', '#e74c3c']  # Green to Red
        self.color_scale_volume = ['#ecf0f1', '#3498db', '#2c3e50']   # Light to Dark

    def create_static_heatmap(
        self,
        data: pd.DataFrame,
        value_column: str = 'population_per_surgery',
        title: str = 'Healthcare Coldspot Analysis',
        output_file: str = 'coldspot_heatmap.png',
        figsize: Tuple[int, int] = (15, 10)
    ):
        """
        Create static heatmap using matplotlib.

        Args:
            data: DataFrame with coldspot analysis
            value_column: Column to visualize
            title: Plot title
            output_file: Output filename
            figsize: Figure size
        """
        logger.info("Creating static heatmap...")

        plt.figure(figsize=figsize)

        # Sort by severity for better visualization
        plot_data = data.sort_values(value_column, ascending=False).head(30)

        # Create color map based on coldspot status
        colors = plot_data['is_coldspot'].map({True: '#e74c3c', False: '#2ecc71'})

        # Create bar plot
        plt.barh(
            range(len(plot_data)),
            plot_data[value_column],
            color=colors,
            alpha=0.7
        )

        plt.yticks(range(len(plot_data)), plot_data['msa_name'], fontsize=8)
        plt.xlabel('Population per Surgery', fontsize=12)
        plt.title(title, fontsize=14, fontweight='bold')

        # Add median line
        median_val = data[value_column].median()
        plt.axvline(x=median_val, color='blue', linestyle='--', label='National Median')

        # Add coldspot threshold line
        if 'coldspot_threshold' in data.columns:
            threshold = data['coldspot_threshold'].iloc[0]
            plt.axvline(x=threshold, color='red', linestyle='--', label='Coldspot Threshold')

        plt.legend()
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Static heatmap saved to {output_file}")

    def create_interactive_map(
        self,
        data: pd.DataFrame,
        value_column: str = 'population_per_surgery',
        title: str = 'Interactive Coldspot Map',
        output_file: str = 'coldspot_map.html'
    ):
        """
        Create interactive choropleth map using Plotly.

        Args:
            data: DataFrame with coldspot analysis
            value_column: Column to visualize
            title: Map title
            output_file: Output HTML filename
        """
        if not PLOTLY_AVAILABLE:
            logger.error("Plotly required for interactive maps")
            return

        logger.info("Creating interactive map...")

        # Prepare data
        data['text'] = data.apply(
            lambda row: f"{row['msa_name']}<br>"
                       f"Population: {row['population']:,.0f}<br>"
                       f"Surgeries: {row['total_surgeries']:,.0f}<br>"
                       f"Pop/Surgery: {row['population_per_surgery']:.0f}<br>"
                       f"Coldspot: {'Yes' if row['is_coldspot'] else 'No'}",
            axis=1
        )

        # Create figure
        fig = go.Figure()

        # Add coldspots
        coldspots = data[data['is_coldspot']]
        fig.add_trace(go.Scattergeo(
            lon=coldspots.get('longitude', []),
            lat=coldspots.get('latitude', []),
            text=coldspots['text'],
            mode='markers',
            marker=dict(
                size=coldspots[value_column] / 1000,  # Scale marker size
                color='red',
                opacity=0.7,
                line=dict(width=0.5, color='darkred')
            ),
            name='Coldspots'
        ))

        # Add normal areas
        normal = data[~data['is_coldspot']]
        fig.add_trace(go.Scattergeo(
            lon=normal.get('longitude', []),
            lat=normal.get('latitude', []),
            text=normal['text'],
            mode='markers',
            marker=dict(
                size=normal[value_column] / 1000,
                color='green',
                opacity=0.5,
                line=dict(width=0.5, color='darkgreen')
            ),
            name='Adequate Coverage'
        ))

        # Update layout
        fig.update_layout(
            title=title,
            geo=dict(
                scope='usa',
                projection_type='albers usa',
                showland=True,
                landcolor='rgb(243, 243, 243)',
                coastlinecolor='rgb(204, 204, 204)',
            ),
            height=600,
        )

        fig.write_html(output_file)
        logger.info(f"Interactive map saved to {output_file}")

    def create_dashboard(
        self,
        data: pd.DataFrame,
        output_file: str = 'coldspot_dashboard.html'
    ):
        """
        Create comprehensive dashboard with multiple visualizations.

        Args:
            data: DataFrame with coldspot analysis
            output_file: Output HTML filename
        """
        if not PLOTLY_AVAILABLE:
            logger.error("Plotly required for dashboard")
            return

        logger.info("Creating dashboard...")

        from plotly.subplots import make_subplots

        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Surgery Rate Distribution',
                'Population vs Surgeries',
                'Top 10 Coldspots',
                'Geographic Distribution'
            ),
            specs=[
                [{'type': 'histogram'}, {'type': 'scatter'}],
                [{'type': 'bar'}, {'type': 'scatter'}]
            ]
        )

        # 1. Surgery rate distribution
        fig.add_trace(
            go.Histogram(
                x=data['surgeries_per_100k'],
                nbinsx=30,
                name='Surgery Rate',
                marker_color='lightblue'
            ),
            row=1, col=1
        )

        # 2. Population vs Surgeries scatter
        fig.add_trace(
            go.Scatter(
                x=data['population'],
                y=data['total_surgeries'],
                mode='markers',
                marker=dict(
                    size=8,
                    color=data['is_coldspot'].map({True: 'red', False: 'green'}),
                    opacity=0.6
                ),
                text=data['msa_name'],
                name='MSAs'
            ),
            row=1, col=2
        )

        # 3. Top 10 coldspots
        top_coldspots = data[data['is_coldspot']].nlargest(10, 'severity_score')
        fig.add_trace(
            go.Bar(
                y=top_coldspots['msa_name'],
                x=top_coldspots['population_per_surgery'],
                orientation='h',
                marker_color='red',
                name='Coldspots'
            ),
            row=2, col=1
        )

        # Update layout
        fig.update_layout(
            height=800,
            showlegend=True,
            title_text="Cranial Tumor Surgery Coldspot Analysis Dashboard"
        )

        fig.update_xaxes(title_text="Surgeries per 100k", row=1, col=1)
        fig.update_xaxes(title_text="Population", row=1, col=2)
        fig.update_xaxes(title_text="Population per Surgery", row=2, col=1)

        fig.update_yaxes(title_text="Frequency", row=1, col=1)
        fig.update_yaxes(title_text="Total Surgeries", row=1, col=2)
        fig.update_yaxes(title_text="MSA", row=2, col=1)

        fig.write_html(output_file)
        logger.info(f"Dashboard saved to {output_file}")

    def create_comparison_chart(
        self,
        data: pd.DataFrame,
        output_file: str = 'msa_comparison.png'
    ):
        """
        Create comparison chart of top and bottom MSAs.

        Args:
            data: DataFrame with coldspot analysis
            output_file: Output filename
        """
        logger.info("Creating comparison chart...")

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

        # Top 10 MSAs with best coverage
        best = data.nsmallest(10, 'population_per_surgery')
        ax1.barh(
            range(len(best)),
            best['population_per_surgery'],
            color='#2ecc71',
            alpha=0.7
        )
        ax1.set_yticks(range(len(best)))
        ax1.set_yticklabels(best['msa_name'], fontsize=9)
        ax1.set_xlabel('Population per Surgery', fontsize=11)
        ax1.set_title('Top 10 MSAs - Best Coverage', fontsize=12, fontweight='bold')
        ax1.invert_yaxis()

        # Top 10 coldspots (worst coverage)
        worst = data[data['is_coldspot']].nlargest(10, 'population_per_surgery')
        ax2.barh(
            range(len(worst)),
            worst['population_per_surgery'],
            color='#e74c3c',
            alpha=0.7
        )
        ax2.set_yticks(range(len(worst)))
        ax2.set_yticklabels(worst['msa_name'], fontsize=9)
        ax2.set_xlabel('Population per Surgery', fontsize=11)
        ax2.set_title('Top 10 Coldspots - Worst Coverage', fontsize=12, fontweight='bold')
        ax2.invert_yaxis()

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Comparison chart saved to {output_file}")

    def generate_summary_table(
        self,
        data: pd.DataFrame,
        output_file: str = 'summary_table.html'
    ):
        """
        Generate HTML summary table.

        Args:
            data: DataFrame with coldspot analysis
            output_file: Output HTML filename
        """
        logger.info("Generating summary table...")

        # Select key columns
        summary = data[[
            'msa_name', 'population', 'total_surgeries',
            'surgeries_per_100k', 'population_per_surgery',
            'is_coldspot', 'severity_score'
        ]].copy()

        # Format numbers
        summary['population'] = summary['population'].apply(lambda x: f"{x:,.0f}")
        summary['total_surgeries'] = summary['total_surgeries'].apply(lambda x: f"{x:,.0f}")
        summary['surgeries_per_100k'] = summary['surgeries_per_100k'].apply(lambda x: f"{x:.2f}")
        summary['population_per_surgery'] = summary['population_per_surgery'].apply(lambda x: f"{x:.0f}")
        summary['severity_score'] = summary['severity_score'].apply(lambda x: f"{x:.2f}")

        # Rename columns
        summary.columns = [
            'MSA', 'Population', 'Total Surgeries',
            'Surgeries per 100k', 'Population per Surgery',
            'Coldspot', 'Severity Score'
        ]

        # Convert to HTML with styling
        html = summary.to_html(
            index=False,
            classes='table table-striped',
            escape=False
        )

        # Add bootstrap CSS
        html_with_style = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
            <style>
                .coldspot-true {{ background-color: #ffcccc; }}
                .coldspot-false {{ background-color: #ccffcc; }}
            </style>
        </head>
        <body>
            <div class="container mt-4">
                <h2>Cranial Tumor Surgery Coldspot Analysis</h2>
                {html}
            </div>
        </body>
        </html>
        """

        with open(output_file, 'w') as f:
            f.write(html_with_style)

        logger.info(f"Summary table saved to {output_file}")


if __name__ == "__main__":
    # Example usage
    # Create sample data
    sample_data = pd.DataFrame({
        'msa_name': ['New York', 'Los Angeles', 'Rural Area 1', 'Rural Area 2'],
        'population': [19000000, 13000000, 500000, 300000],
        'total_surgeries': [1500, 1100, 25, 10],
        'surgeries_per_100k': [7.89, 8.46, 5.0, 3.33],
        'population_per_surgery': [12666, 11818, 20000, 30000],
        'is_coldspot': [False, False, True, True],
        'severity_score': [0.1, 0.0, 1.5, 2.3]
    })

    generator = HeatmapGenerator()
    generator.create_static_heatmap(sample_data)
    generator.create_comparison_chart(sample_data)

    print("Sample visualizations created")
