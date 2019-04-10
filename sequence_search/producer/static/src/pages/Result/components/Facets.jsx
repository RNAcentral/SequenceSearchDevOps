import React from 'react';

import routes from 'services/routes.jsx';


class Result extends React.Component {
  constructor(props) {
    super(props);

    this.renderFacet = this.renderFacet.bind(this);
  }

  renderFacet(facet) {
    return [
      <legend key={`legend-${facet.id}`}><h5 style={{color: 'rgb(0,124,130)' }}>{ facet.label }</h5></legend>,
      <ul key={facet.id} className="vertical menu facet">
        {
          facet.facetValues.map(facetValue => (
            <li key={`li ${facetValue.label}`}>
            <span className="facetValue">
              <input id={`checkbox-${facet.id}-${facetValue.value}`} type="checkbox"
                checked={this.props.selectedFacets.hasOwnProperty(facet.id) && this.props.selectedFacets[facet.id].indexOf(facetValue.value) !== -1}
                onChange={(e) => {
                  this.props.toggleFacet(facet.id, facetValue.value)
                }}/>
              <label htmlFor={`checkbox-${facet.id}-${facetValue.value}`}>{facetValue.label}&nbsp;<small>({facetValue.count})</small></label>
            </span>
            </li>
          ))
        }
      </ul>,
      <br key={`br-${facet.id}`} />
    ];
  }

  render() {
    return (
      <div className="small-12 medium-2 medium-pull-10 columns">
        <section>
          <div>
            { this.props.facets.map(facet => this.renderFacet(facet)) }
          </div>
          {
            this.props.textSearchError &&
            <div className="callout alert">
              <h3>Failed to retrieve text search data.</h3>
              <a onClick={ this.props.onReload }><i className="icon icon-functional" data-icon="R"></i> Reload</a>
            </div>
          }
          <small className="text-muted">
            Powered by <a href="http://www.ebi.ac.uk/ebisearch/" target="_blank">EBI Search</a>
          </small>
        </section>
      </div>
    )
  }
}

export default Result;