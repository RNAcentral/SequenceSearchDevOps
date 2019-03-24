import React from 'react';

import routes from 'services/routes.jsx';


class Dashboard extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      consumers: []
    };

    this.pollConsumersStatus = this.pollConsumersStatus.bind(this);
    this.consumerStatusIcon = this.consumerStatusIcon.bind(this);
  }

  pollConsumersStatus() {
    fetch(routes.consumersStatuses())
      .then(response => response.json())
      .then(data => {
          this.setState({ consumers: data });
          this.consumerStatusTimeout = setTimeout(this.getStatus, 1000);
      })
      .catch(reason => this.props.history.push(`/error`));
  }

  consumerStatusIcon(status) {
    if (status === 'available') return (<i className="icon icon-functional" style={{color: "green"}} data-icon="/"/>);
    else if (status === 'busy') return (<i className="icon icon-functional spin" data-icon="s"/>);
    else if (status === 'error') return (<i className="icon icon-generic" style={{color: "red"}} data-icon="l"/>);
  }

  componentDidMount() {
    this.pollConsumersStatus();
  }

  componentWillUnmount() {
    if (this.consumerStatusTimeout) {
      window.clearTimeout(this.consumerStatusTimeout);
    }
  }

  render() {
    return (
      <div className="row">
        <div className="col-lg-12">
          <div className="hpanel">
            <div className="panel-heading">
              <h1>Consumers</h1>
            </div>
            <div className="panel-body">
              <table className="responsive-table">
                <thead>
                  <tr>
                    <th>Consumer</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  { this.state.consumers.map((consumer, index) => (
                    <tr key={index}>
                      <td>{ consumer.ip }</td>
                      <td>{ this.consumerStatusIcon(consumer.status) } { consumer.status }</td>
                    </tr>)) }
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    )
  }
}

export default Dashboard;