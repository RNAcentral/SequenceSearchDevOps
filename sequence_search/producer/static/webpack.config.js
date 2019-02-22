const path = require('path');
const webpack = require('webpack');

const HtmlWebpackPlugin = require('html-webpack-plugin');
const ExtractTextPlugin = require('extract-text-webpack-plugin');

module.exports = function(env) {
  // set variables, modifying the config for dev, prod and ssr
  // see: https://github.com/webpack/webpack/issues/2254
  let environment;
  if (env && env.prod) environment = 'production';
  else environment = 'development';

  return {
    target: 'web',
    entry: path.join(__dirname, 'src', 'app.jsx'),
    output: {
      path: path.join(__dirname, 'dist'),
      publicPath: '/dist/', // environment === 'production' ? '/dist/' : '/',
      filename: 'app.[hash:7].js'
    },
    resolve: {
      modules: [path.join(__dirname, 'src'), path.join(__dirname, 'node_modules')]
    },
    plugins: [
      new webpack.HotModuleReplacementPlugin(),
      new ExtractTextPlugin('app.[hash:7].css'),
      new HtmlWebpackPlugin({
        inject: "body",
        template: "src/index.html",
        filename: environment === 'production' ? path.join(__dirname, "index.html") : "index.html"
      }),
      new webpack.ProvidePlugin({ $: 'jquery', jQuery: 'jquery', jquery: 'jquery' })
    ],
    module: {
      rules: [
        {
          test: /\.jsx?$/,
          loader: 'babel-loader',
          exclude: /node_modules/,
          query: {
            presets: ['es2015', 'react'],
            plugins: ['transform-es2015-destructuring', 'transform-object-rest-spread']
          }
        },
        {
          test: /\.(s?css|sass)$/,
          use: ExtractTextPlugin.extract({
            use: [
              { loader: 'css-loader', options: {sourceMap: true} },
              { loader: 'sass-loader', options: {sourceMap: true} }
            ]
          })
        },
        {
          test: /\.(png|jpe?g|gif)(\?v=\d+\.\d+\.\d+)?$/,
          loader: 'file-loader' // 'url-loader?limit=10000'
        },
        {
          test: /\.(eot|com|json|ttf|woff|woff2)(\?v=\d+\.\d+\.\d+)?$/,
          loader: 'file-loader' // 'url-loader?limit=10000&mimetype=application/octet-stream'
        },
        {
          test: /\.svg(\?v=\d+\.\d+\.\d+)?$/,
          loader: 'file-loader' // 'url-loader?limit=10000&mimetype=image/svg+xml'
        }
      ]
    },
    // A good explanation of how contentBase and publicPath work:
    // https://github.com/webpack/docs/wiki/webpack-dev-server
    devServer: {
      publicPath: '/dist', // suffix of bundle url in index.html that makes it localhost:8080<publicPath>/app.4d9882a.js
      // contentBase: './', // location of index.html that webpack-dev-server creates in memory-fs
      hot: true,
      proxy: { // requests to these urls are proxied to the real backend server
        '/api': {
            target: 'http://localhost:8002',
            secure: false
        }
    }
    },
    devtool: "source-map"
  };
};